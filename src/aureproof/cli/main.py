# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Aureproof command-line interface (plan v2 §3.9, issue #16).

Offline commands work on saved records only; nothing here contacts a model.

Exit codes: 0 = success; 1 = a check failed (invalid bundle, re-score mismatch,
or not re-scorable); 2 = usage or I/O error (missing path, symlink, unsafe path).
"""

from __future__ import annotations

import json
import secrets
import sys
from pathlib import Path
from typing import Annotated

import typer

from aureproof import __version__
from aureproof.bundle import validate as validate_bundle
from aureproof.bundle.run import rescore
from aureproof.cli.report import collect, render_html, render_markdown
from aureproof.storage import StorageError, read_bundle

app = typer.Typer(
    name="aureproof",
    help="Integrity layer for AI-agent evaluations.",
    no_args_is_help=True,
    add_completion=False,
)

BundleArg = Annotated[Path, typer.Argument(help="Bundle directory.")]
TrustedOpt = Annotated[
    str | None,
    typer.Option(
        "--trusted-seal-digest", help="sha256:<hex> of seal.intoto.json, recorded elsewhere."
    ),
]
JsonOpt = Annotated[bool, typer.Option("--json", help="Machine-readable output.")]


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"aureproof {__version__}")
        raise typer.Exit


@app.callback()
def main(
    _version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show the Aureproof version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Aureproof: every claim, backed by evidence."""


def _read(bundle: Path) -> dict[str, bytes]:
    try:
        return read_bundle(bundle)
    except StorageError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc


@app.command()
def validate(
    bundle: BundleArg, trusted_seal_digest: TrustedOpt = None, as_json: JsonOpt = False
) -> None:
    """Validate a bundle offline (checks V1-V6)."""
    report = validate_bundle(_read(bundle), trusted_seal_digest=trusted_seal_digest)
    if as_json:
        typer.echo(
            json.dumps(
                {
                    "valid": report.valid,
                    "checks": [
                        {"id": c.id, "name": c.name, "status": c.status, "problems": c.problems}
                        for c in report.checks
                    ],
                },
                indent=2,
            )
        )
    else:
        for c in report.checks:
            typer.echo(f"{c.id} {c.name:<20} {c.status}")
            for p in c.problems:
                typer.echo(f"    - {p}")
        typer.echo("VALID" if report.valid else "INVALID")
    raise typer.Exit(0 if report.valid else 1)


@app.command()
def score(
    bundle: BundleArg,
    offline: Annotated[
        bool, typer.Option("--offline", help="Re-score from saved records.")
    ] = False,
    trusted_seal_digest: TrustedOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Re-score a sealed run bundle from saved records and compare byte for byte."""
    if not offline:
        typer.echo("error: only --offline scoring exists in v0.1", err=True)
        raise typer.Exit(2)
    files = _read(bundle)
    report = validate_bundle(files, trusted_seal_digest=trusted_seal_digest)
    if not report.valid:
        typer.echo("INVALID bundle; refusing to re-score:", err=True)
        for p in report.problems():
            typer.echo(f"  - {p}", err=True)
        raise typer.Exit(1)
    result = rescore(files)
    if as_json:
        typer.echo(
            json.dumps(
                {"status": result.status, "problems": result.problems, "metrics": result.metrics},
                indent=2,
            )
        )
    else:
        typer.echo(f"re-score: {result.status}")
        for p in result.problems:
            typer.echo(f"  - {p}")
        for name, m in ((result.metrics or {}).get("metrics") or {}).items():
            value = "undefined" if m.get("value") is None else f"{m['value']:.4f}"
            typer.echo(f"  {name:<28} {m['numerator']}/{m['denominator']}  {value}")
    raise typer.Exit(0 if result.status == "reproduced" else 1)


@app.command()
def report(
    bundle: BundleArg,
    out: Annotated[Path, typer.Option("--out", help="Report file to write.")],
    fmt: Annotated[str, typer.Option("--format", help="html or md.")] = "html",
    trusted_seal_digest: TrustedOpt = None,
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing report.")] = False,
) -> None:
    """Write an HTML or Markdown report. Exit 1 if the bundle is invalid or does not re-score."""
    if fmt not in ("html", "md"):
        typer.echo("error: --format must be html or md", err=True)
        raise typer.Exit(2)
    if (out.exists() or out.is_symlink()) and not force:
        typer.echo(f"error: {out} exists (use --force)", err=True)
        raise typer.Exit(2)
    files = _read(bundle)
    validation = validate_bundle(files, trusted_seal_digest=trusted_seal_digest)
    result = rescore(files) if validation.valid else None
    data = collect(files, validation, result, trusted_seal_digest is not None)
    text = render_html(data) if fmt == "html" else render_markdown(data)
    tmp = out.parent / f".{out.name}.tmp-{secrets.token_hex(6)}"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(out)
    ok = validation.valid and result is not None and result.status == "reproduced"
    typer.echo(f"wrote {out} ({'ok' if ok else 'with problems'})")
    raise typer.Exit(0 if ok else 1)


task_app = typer.Typer(help="Task health: calibration and qualification.", no_args_is_help=True)
app.add_typer(task_app, name="task")


@task_app.command("validate")
def task_validate(
    task_id: Annotated[str, typer.Argument(help="Task ID, e.g. authz-001.")],
    root: Annotated[Path, typer.Option("--root", help="Repository root.")] = Path(),
    out: Annotated[Path | None, typer.Option("--out", help="Write the THR JSON here.")] = None,
    as_json: JsonOpt = False,
) -> None:
    """Run every THR control twice, label lint, and canary checks. Exit 1 unless healthy."""
    from aureproof.oracles.calibration import calibrate, qualification_problems

    if not (root / "fixtures" / "security" / task_id).is_dir():
        typer.echo(f"error: no fixture for task {task_id!r} under {root}", err=True)
        raise typer.Exit(2)
    problems = qualification_problems(root, task_id)
    record = calibrate(root, task_id)
    if out is not None:
        if out.exists():
            typer.echo(f"error: {out} exists", err=True)
            raise typer.Exit(2)
        out.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    if as_json:
        typer.echo(
            json.dumps(
                {
                    "status": record.status.value,
                    "reason": record.status_reason,
                    "qualification_problems": problems,
                    "record": record.model_dump(mode="json"),
                },
                indent=2,
            )
        )
    else:
        for c in record.controls:
            state = {True: "pass", False: "FAIL", None: "not run"}[c.passed]
            typer.echo(f"{c.kind.value:<20} {state}")
        typer.echo(f"determinism          {record.determinism.reproduced}")
        for p in problems:
            typer.echo(f"  - {p}")
        typer.echo(f"{task_id}: {record.status.value.upper()} ({record.status_reason})")
        typer.echo("note: unreviewed and unfrozen until an independent reviewer signs off (#31)")
    raise typer.Exit(0 if record.status.value == "healthy" and not problems else 1)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
