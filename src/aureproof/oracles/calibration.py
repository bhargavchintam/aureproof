# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Calibration runner: produce a Task Health Record for a fixture (issue #38).

Adapter (file and process I/O). Runs the seven required controls of
specs/thr §3 through the real scoring core, plus the evaluator's calibration PoC
(trusted, evaluator-authored code; never agent code), then re-runs every
control and compares the outcomes. The record is returned unreviewed and
unfrozen: only an independent reviewer may freeze it (ADR-0005).
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aureproof import __version__
from aureproof.bundle.canonical import digest_ref
from aureproof.contracts import EpisodeSignals, LabelSet, RunnerOutcome, TaskSpec
from aureproof.contracts.dataset import DatasetRegistry
from aureproof.contracts.labels_lint import lint_labels
from aureproof.contracts.thr import (
    ControlKind,
    ControlResult,
    Determinism,
    TaskHealthRecord,
    derive_status,
)
from aureproof.oracles.python_spans import line_counts, python_spans
from aureproof.scoring import compute_metrics, score_episode, scoring_identity

OK = EpisodeSignals(evidence_complete=True, runner_outcome=RunnerOutcome.OK)
SPRAY_MAX_YIELD = 0.25  # spray_cheat passes only if strict yield collapses to <= this
POC_TIMEOUT_S = 60


@dataclass(frozen=True)
class Paths:
    root: Path
    task_id: str

    @property
    def security(self) -> Path:
        return self.root / "fixtures" / "security" / self.task_id

    @property
    def oracles(self) -> Path:
        return self.root / "fixtures" / "oracles" / self.task_id

    def variant(self, name: str) -> Path:
        return self.security / "variants" / name


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def registry(root: Path) -> DatasetRegistry:
    return DatasetRegistry.model_validate_json((root / "fixtures/dataset.json").read_text("utf-8"))


def task_spec(root: Path, task_id: str) -> TaskSpec:
    """The task by content, from the fixture tree and the dataset registry."""
    p, reg = Paths(root, task_id), registry(root)
    entry = next(t for t in reg.tasks if t.task_id == task_id)
    labels = LabelSet.model_validate_json((p.oracles / "labels.json").read_text("utf-8"))
    views = {}
    for variant in ("vulnerable", "repaired"):
        base = p.variant(variant)
        views[variant] = {
            "root": base.relative_to(root).as_posix(),
            "instruction": {
                "path": (p.security / "instruction.md").relative_to(root).as_posix(),
                "sha256": _sha(p.security / "instruction.md"),
            },
            "files": [
                {"path": f.relative_to(base).as_posix(), "sha256": _sha(f)}
                for f in sorted(base.rglob("*.py"))
            ],
        }
    return TaskSpec.model_validate(
        {
            "task_id": task_id,
            "task_revision": entry.task_revision,
            "dataset_id": reg.dataset_id,
            "dataset_revision": reg.dataset_revision,
            "family": "security-discovery",
            "cluster_id": labels.cluster_id or task_id,
            "canary_id": entry.canary,
            "agent_views": views,
            "labels": {
                "path": (p.oracles / "labels.json").relative_to(root).as_posix(),
                "sha256": _sha(p.oracles / "labels.json"),
            },
        }
    )


def _score(labels: LabelSet, view: dict[str, int], variant: str, findings: Any) -> Any:
    data = findings if isinstance(findings, bytes) else json.dumps(findings).encode()
    return score_episode(data, OK, labels, variant=variant, agent_view=view), data


def _finding(file: str, symbol: str, cwe: int) -> dict[str, Any]:
    return {
        "cwe": cwe,
        "locations": [{"file": file, "symbol": symbol}],
        "description": "calibration control",
    }


def _poc(p: Paths, variant: str) -> dict[str, Any]:
    poc = p.oracles / "calibration_poc.py"
    out = subprocess.run(
        [sys.executable, "-B", str(poc), str(p.variant(variant))],
        capture_output=True,
        text=True,
        timeout=POC_TIMEOUT_S,
        check=False,
    )
    if out.returncode != 0:
        return {"error": out.stderr[-500:]}
    result: dict[str, Any] = json.loads(out.stdout)
    return result


def run_controls(root: Path, task_id: str, run_id: str) -> list[ControlResult]:
    p = Paths(root, task_id)
    labels = LabelSet.model_validate_json((p.oracles / "labels.json").read_text("utf-8"))
    views = {v: line_counts(p.variant(v)) for v in ("vulnerable", "repaired")}
    spans = {v: python_spans(p.variant(v)) for v in ("vulnerable", "repaired")}
    controls: list[ControlResult] = []

    def add(
        kind: str,
        variant: str | None,
        data: bytes,
        expected: Any,
        observed: Any,
        passed: bool | None,
        note: str | None = None,
    ) -> None:
        controls.append(
            ControlResult(
                kind=ControlKind(kind),
                variant=variant,  # type: ignore[arg-type]
                input_digest=digest_ref(data),
                expected=expected,
                observed=observed,
                passed=passed,
                run_ids=[run_id],
                note=note,
            )
        )

    problems = lint_labels(labels, views, spans)
    add("label_lint", None, (p.oracles / "labels.json").read_bytes(), [], problems, not problems)

    present = sorted(d.defect_id for d in labels.defects if "vulnerable" in d.variants)
    reference = [
        _finding(d.anchors[0].file, d.anchors[0].symbol, d.accepted_cwes[0])
        for d in labels.defects
        if "vulnerable" in d.variants
    ]
    score, data = _score(labels, views["vulnerable"], "vulnerable", reference)
    credited = sorted(score.credited)
    add(
        "reference_positive",
        "vulnerable",
        data,
        {"credited": present},
        {"credited": credited},
        credited == present,
    )

    if labels.focal_negative is not None:
        fn = labels.focal_negative
        focal = [_finding(a.file, a.symbol, labels.defects[0].accepted_cwes[0]) for a in fn.anchors]
        score, data = _score(labels, views[fn.variant], fn.variant, focal)
        verdicts = [v.verdict.value for v in score.verdicts or ()]
        add(
            "repaired_negative",
            fn.variant,
            data,
            ["refuted"] * len(focal),
            verdicts,
            verdicts == ["refuted"] * len(focal),
        )
    else:
        add("repaired_negative", None, b"", "refuted", None, None, note="no focal negative labeled")

    score, data = _score(labels, views["vulnerable"], "vulnerable", [])
    recall = compute_metrics([score])["known_defect_recall"]
    add(
        "nop",
        "vulnerable",
        data,
        {"recall": "0/" + str(len(present))},
        {"recall": f"{recall.numerator}/{recall.denominator}"},
        recall.numerator == 0,
    )

    cwes = sorted({c for d in labels.defects for c in d.accepted_cwes})
    spray = [
        _finding(f, s, c)
        for f, syms in sorted(spans["vulnerable"].items())
        for s in sorted(syms)
        for c in cwes
    ]
    score, data = _score(labels, views["vulnerable"], "vulnerable", spray[:256])
    m = compute_metrics([score])
    rec, yld = m["known_defect_recall"], m["strict_confirmed_yield"]
    observed = {
        "recall": f"{rec.numerator}/{rec.denominator}",
        "strict_yield": f"{yld.numerator}/{yld.denominator}",
    }
    add(
        "spray_cheat",
        "vulnerable",
        data,
        {"recall": f"{len(present)}/{len(present)}", "strict_yield_at_most": SPRAY_MAX_YIELD},
        observed,
        rec.numerator == rec.denominator and (yld.value or 0) <= SPRAY_MAX_YIELD,
    )

    score, data = _score(labels, views["vulnerable"], "vulnerable", b"[{")
    add(
        "malformed",
        "vulnerable",
        data,
        "invalid_output",
        score.disposition.value,
        score.disposition.value == "invalid_output",
    )

    vulnerable, repaired = _poc(p, "vulnerable"), _poc(p, "repaired")
    expected_poc = {
        "vulnerable": {"reference_positive": True, "irrelevant_trigger": False, "malformed": False},
        "repaired": {"reference_positive": False, "irrelevant_trigger": False, "malformed": False},
    }
    if "error" in vulnerable or "error" in repaired:
        add(
            "calibration_poc",
            None,
            (p.oracles / "calibration_poc.py").read_bytes(),
            expected_poc,
            {"vulnerable": vulnerable, "repaired": repaired},
            None,
            note="calibration PoC could not run",
        )
    else:
        observed_poc = {
            name: {k: bool(res[k]["triggered"]) for k in expected_poc[name]}
            for name, res in (("vulnerable", vulnerable), ("repaired", repaired))
        }
        add(
            "calibration_poc",
            None,
            (p.oracles / "calibration_poc.py").read_bytes(),
            expected_poc,
            observed_poc,
            observed_poc == expected_poc,
        )
    return controls


def environment() -> dict[str, str]:
    lock = Path(__file__).resolve().parents[3] / "uv.lock"
    identity = {
        "python": sys.version,
        "implementation": platform.python_implementation(),
        "uv_lock": _sha(lock) if lock.exists() else "absent",
    }
    return {
        "runner": "aureproof-calibration",
        "runner_version": __version__,
        "image_digest": digest_ref(identity),
        "platform": f"{sys.platform}/{platform.machine()}",
    }


def calibrate(root: Path, task_id: str) -> TaskHealthRecord:
    """Run every control twice; derive status. Unreviewed and unfrozen."""
    first = run_controls(root, task_id, "calibration-1")
    second = run_controls(root, task_id, "calibration-2")
    reproduced = [(c.kind, c.observed, c.passed) for c in first] == [
        (c.kind, c.observed, c.passed) for c in second
    ]
    determinism = Determinism(rerun_ids=["calibration-2"], reproduced=reproduced)
    status, reason = derive_status(first, determinism)
    entry = next(t for t in registry(root).tasks if t.task_id == task_id)
    spec = task_spec(root, task_id)
    env = environment()
    limits = ["Synthetic fixture: controlled skills, not real-world capability."]
    if not env["platform"].startswith("linux"):
        limits.append(f"Calibrated on {env['platform']}; Linux host qualification pending (#32).")
    return TaskHealthRecord.model_validate(
        {
            "thr_version": "0.1",
            "task": {
                "task_id": task_id,
                "task_revision": spec.task_revision,
                "task_identity": spec.identity,
            },
            "environment": env,
            "scoring_identity": scoring_identity(),
            "controls": [c.model_dump(mode="json") for c in first],
            "determinism": determinism.model_dump(mode="json"),
            "difficulty_probe": None,
            "status": status.value,
            "status_reason": reason,
            "known_limits": limits,
            "reviewed_by": [],
            "frozen_at": None,
            "canary_id": entry.canary,
            "provenance": {"authorship": "self-authored", "license": "CC-BY-4.0"},
        }
    )


def qualification_problems(root: Path, task_id: str) -> list[str]:
    """Canary and registry checks that must pass before a task can qualify."""
    p, problems = Paths(root, task_id), []
    entry = next((t for t in registry(root).tasks if t.task_id == task_id), None)
    if entry is None:
        return [f"{task_id} is not registered in fixtures/dataset.json"]
    agent = sorted(f for f in p.security.rglob("*") if f.is_file())
    oracle = sorted(f for f in p.oracles.rglob("*") if f.is_file())
    for path in agent + oracle:
        if entry.canary not in path.read_text("utf-8"):
            problems.append(f"public canary missing: {path.relative_to(root)}")
    for path in oracle:
        if entry.oracle_canary not in path.read_text("utf-8"):
            problems.append(f"oracle canary missing: {path.relative_to(root)}")
    for path in agent:
        if entry.oracle_canary in path.read_text("utf-8"):
            problems.append(f"oracle canary leaked into agent view: {path.relative_to(root)}")
    return problems
