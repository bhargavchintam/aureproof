# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Spike grading through the canonical core (issue #34, AP-055).

No Inspect import: this module is exercised in ordinary CI. The spike adds only
what a runner adapter must supply: the captured submission and the agent view
read from the fixture. Every verdict comes from ``aureproof.scoring``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aureproof.contracts import EpisodeSignals, LabelSet, RunnerOutcome
from aureproof.scoring import score_episode

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "security"
ORACLES = ROOT / "fixtures" / "oracles"
OK = EpisodeSignals(evidence_complete=True, runner_outcome=RunnerOutcome.OK)


def load_labels(task_id: str) -> LabelSet:
    return LabelSet.model_validate_json((ORACLES / task_id / "labels.json").read_text("utf-8"))


def agent_view(task_id: str, variant: str) -> dict[str, int]:
    """``{path: line_count}`` of what the agent sees, as mounted at the workspace root."""
    base = FIXTURES / task_id / "variants" / variant
    return {
        p.relative_to(base).as_posix(): len(p.read_text("utf-8").splitlines())
        for p in sorted(base.rglob("*.py"))
    }


def grade(
    capture: dict[str, Any] | None,
    *,
    task_id: str,
    variant: str,
    signals: EpisodeSignals = OK,
) -> dict[str, Any]:
    """Grade a captured submission. ``capture`` is the spike's logged store record."""
    data = None
    if capture and capture.get("status") == "captured":
        data = str(capture["text"]).encode("utf-8")
    result = score_episode(
        data,
        signals,
        load_labels(task_id),
        variant=variant,
        agent_view=agent_view(task_id, variant),
    )
    return {
        "disposition": result.disposition.value,
        "verdicts": [
            {k: v for k, v in r.model_dump(mode="json").items() if v is not None}
            for r in result.verdicts or ()
        ],
        "credited": list(result.credited),
        "annotations": list(result.annotations),
        "findings_sha256": (capture or {}).get("sha256"),
    }


def verdict_summary(graded: dict[str, Any]) -> list[str]:
    return [str(v["verdict"]) for v in graded["verdicts"]]


if __name__ == "__main__":  # pragma: no cover - manual check
    print(json.dumps(agent_view("authz-001", "vulnerable"), indent=2))
