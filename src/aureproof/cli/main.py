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
from aureproof.bundle.validate import SignatureCheck
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


IdentityOpt = Annotated[
    str | None,
    typer.Option("--expect-identity", help="Expected signer identity (default: project policy)."),
]
IssuerOpt = Annotated[str | None, typer.Option("--expect-issuer", help="Expected OIDC issuer.")]


def _signature(files: dict[str, bytes], identity: str | None, issuer: str | None) -> SignatureCheck:
    try:
        from aureproof.signing import EXPECTED_IDENTITY, EXPECTED_ISSUER, verify_bundle
    except ImportError as exc:  # pragma: no cover - depends on the installed extras
        typer.echo("error: signature verification needs the `sign` extra", err=True)
        raise typer.Exit(2) from exc
    return verify_bundle(
        files, identity=identity or EXPECTED_IDENTITY, issuer=issuer or EXPECTED_ISSUER
    )


@app.command()
def validate(
    bundle: BundleArg,
    trusted_seal_digest: TrustedOpt = None,
    verify_signature: Annotated[
        bool, typer.Option("--verify-signature", help="Verify seal.sigstore.json offline (V5).")
    ] = False,
    require_signature: Annotated[
        bool,
        typer.Option("--require-signature", help="Fail unless V5 passes (signed-evidence gate)."),
    ] = False,
    public: Annotated[
        bool,
        typer.Option("--public", help="Also require a redacted, label-free, secret-free bundle."),
    ] = False,
    expect_identity: IdentityOpt = None,
    expect_issuer: IssuerOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Validate a bundle offline (checks V1-V6)."""
    from aureproof.bundle.public import public_problems

    files = _read(bundle)
    signature: SignatureCheck | None = None
    if verify_signature or require_signature:
        signature = _signature(files, expect_identity, expect_issuer)
    report = validate_bundle(files, trusted_seal_digest=trusted_seal_digest, signature=signature)
    gate: list[str] = []
    if require_signature and not report.signed:
        gate.append("signed-evidence gate: no verified signature (V5 did not pass)")
    if public:
        gate += [f"public: {p}" for p in public_problems(files)]
    ok = report.valid and not gate
    if as_json:
        typer.echo(
            json.dumps(
                {
                    "valid": report.valid,
                    "signed": report.signed,
                    "ok": ok,
                    "gate_problems": gate,
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
        for p in gate:
            typer.echo(f"GATE {p}")
        typer.echo("VALID" if ok else "INVALID")
    raise typer.Exit(0 if ok else 1)


@app.command()
def sign(
    path: Annotated[Path, typer.Argument(help="Bundle directory, or a canonical JSON file.")],
) -> None:
    """Sign keylessly with the ambient OIDC identity (the sign.yml workflow)."""
    from aureproof.bundle.canonical import canonical_json
    from aureproof.bundle.models import SEAL
    from aureproof.contracts.strict_json import JsonInputError, loads_strict

    try:
        from aureproof.signing import sign_bytes, signature_path, verify_bytes
    except ImportError as exc:  # pragma: no cover
        typer.echo("error: signing needs the `sign` extra", err=True)
        raise typer.Exit(2) from exc
    target = path / SEAL if path.is_dir() else path
    if not target.is_file() or target.is_symlink():
        typer.echo(f"error: {target} is not a regular file", err=True)
        raise typer.Exit(2)
    data = target.read_bytes()
    try:
        if canonical_json(loads_strict(data, i_json=True)) != data:
            raise JsonInputError("not RFC 8785 canonical")
    except JsonInputError as exc:
        typer.echo(f"error: refusing to sign non-canonical JSON: {exc}", err=True)
        raise typer.Exit(2) from exc
    out = signature_path(path)
    if out.exists():
        typer.echo(f"error: {out} exists", err=True)
        raise typer.Exit(2)
    bundle_json = sign_bytes(data)
    check = verify_bytes(data, bundle_json)
    out.write_text(bundle_json, encoding="utf-8")
    typer.echo(f"wrote {out}; verified={check.verified} identity={check.identity}")
    raise typer.Exit(0 if check.verified else 1)


@app.command()
def verify(
    path: Annotated[Path, typer.Argument(help="Bundle directory, or a signed file.")],
    expect_identity: IdentityOpt = None,
    expect_issuer: IssuerOpt = None,
) -> None:
    """Verify a signature offline against the expected signer identity."""
    try:
        from aureproof.signing import (
            EXPECTED_IDENTITY,
            EXPECTED_ISSUER,
            signature_path,
            verify_bytes,
        )
    except ImportError as exc:  # pragma: no cover
        typer.echo("error: verification needs the `sign` extra", err=True)
        raise typer.Exit(2) from exc
    from aureproof.bundle.models import SEAL

    target = path / SEAL if path.is_dir() else path
    sig = signature_path(path)
    if not target.is_file() or not sig.is_file():
        typer.echo(f"error: need both {target} and {sig}", err=True)
        raise typer.Exit(2)
    check = verify_bytes(
        target.read_bytes(),
        sig.read_bytes(),
        identity=expect_identity or EXPECTED_IDENTITY,
        issuer=expect_issuer or EXPECTED_ISSUER,
    )
    typer.echo(f"verified={check.verified} identity={check.identity} issuer={check.issuer}")
    for p in check.problems:
        typer.echo(f"  - {p}")
    raise typer.Exit(0 if check.verified else 1)


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


@task_app.command("probe")
def task_probe(
    task_id: Annotated[str, typer.Argument(help="Task ID, e.g. authz-001.")],
    root: Annotated[Path, typer.Option("--root", help="Repository root.")] = Path(),
    model: Annotated[
        str | None,
        typer.Option("--model", help="Also run the single-shot model baseline (needs a key)."),
    ] = None,
    out: Annotated[
        Path | None, typer.Option("--out", help="Write the THR with its probe here.")
    ] = None,
    as_json: JsonOpt = False,
) -> None:
    """Difficulty probe: Bandit and single-shot baselines. Exit 1 if both solve the task."""
    from aureproof.oracles.calibration import calibrate
    from aureproof.oracles.probe import (
        AnthropicClient,
        SingleShotConfig,
        bandit_baseline,
        saturation,
        single_shot_baseline,
        with_probe,
    )

    if not (root / "fixtures" / "security" / task_id).is_dir():
        typer.echo(f"error: no fixture for task {task_id!r} under {root}", err=True)
        raise typer.Exit(2)
    if out is not None and out.exists():
        typer.echo(f"error: {out} exists", err=True)
        raise typer.Exit(2)
    try:
        static = bandit_baseline(root, task_id)
    except ModuleNotFoundError:
        typer.echo("error: the Bandit probe needs the `baseline` extra", err=True)
        raise typer.Exit(2) from None
    single = None
    if model is not None:
        config = SingleShotConfig(model=model)
        try:
            single = single_shot_baseline(root, task_id, config, AnthropicClient(config))
        except ModuleNotFoundError:
            typer.echo("error: the single-shot probe needs the `inspect` extra", err=True)
            raise typer.Exit(2) from None
    verdict = saturation(static, single)
    record = with_probe(calibrate(root, task_id), static, single)
    if out is not None:
        out.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    runs = [r for r in (static, single) if r is not None]
    if as_json:
        typer.echo(
            json.dumps(
                {
                    "task_id": task_id,
                    "task_identity": record.task.task_identity,
                    "saturation": verdict,
                    "baselines": [
                        {
                            "probe": r.probe,
                            "system_identity": r.system_identity,
                            "solved": r.solved,
                            "metrics": r.metrics,
                            "episodes": [vars(e) for e in r.episodes],
                            "mapping_losses": r.losses,
                        }
                        for r in runs
                    ],
                },
                indent=2,
            )
        )
    else:
        for r in runs:
            typer.echo(f"{r.probe:<18} solved={r.solved}  {r.system_identity}")
            for name in ("known_defect_recall", "strict_confirmed_yield"):
                typer.echo(f"  {name:<24} {r.metrics[name]}")
            for e in r.episodes:
                typer.echo(f"  {e.variant:<10} {e.disposition} {e.verdicts}")
        if single is None:
            typer.echo("single_shot_model  not run (pass --model; needs a provider key, #7)")
        typer.echo(f"{task_id}: {verdict.upper()}")
        if verdict == "saturated":
            typer.echo("both baselines solve it: redesign before benchmark expansion (#44)")
    raise typer.Exit(1 if verdict == "saturated" else 0)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
