# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Collect-then-match grading for the Day-2 Inspect spike (issue #7).

Two steps, split on purpose:

* ``collect_findings`` is a solver step that runs after the agent. It reads
  ``findings.json`` out of the sandbox once and stores the raw text and its
  sha256 in the sample store, which Inspect writes to the log.
* ``findings_matcher`` is the scorer. It reads only the captured bytes from the
  store and the evaluator-only labels on the host. It never touches the sandbox,
  so live scoring and offline re-scoring of a saved log run the same code.

Nothing the agent writes other than ``findings.json`` is ever read; forged
verdict or reward files in the workspace are ignored by construction (ADR-0004).

The matcher is a deliberately small stand-in for AP-007 (rules M1-M9 in
``scoring.md``): file + symbol overlap with an anchor, and the accepted-CWE set.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from inspect_ai.scorer import Score, Target, mean, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import sandbox, store

CAPTURE_KEY = "aureproof_capture"
FINDINGS_FILE = "findings.json"
ORACLES = Path(__file__).resolve().parents[2] / "fixtures" / "oracles"


@solver
def collect_findings() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        try:
            raw = await sandbox().read_file(FINDINGS_FILE, text=True)
        except FileNotFoundError:
            store().set(CAPTURE_KEY, {"status": "no_submission"})
            return state
        store().set(
            CAPTURE_KEY,
            {
                "status": "captured",
                "path": FINDINGS_FILE,
                "sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "text": raw,
            },
        )
        return state

    return solve


def _key(loc: dict[str, Any]) -> tuple[str, str | None]:
    return (str(loc.get("file", "")), loc.get("symbol"))


def _in_scope(loc: dict[str, Any], scope: list[dict[str, Any]]) -> bool:
    file, symbol = _key(loc)
    return any(
        s["file"] == file and (s.get("symbol") is None or s["symbol"] == symbol) for s in scope
    )


def match(findings: list[dict[str, Any]], labels: dict[str, Any], variant: str) -> list[str]:
    """Return one verdict per finding. Pure: no I/O, deterministic."""
    defects = [d for d in labels["defects"] if d["variant"] == variant]
    focal = labels["focal_negative"]
    scope = labels["reviewed_negative_scope"]
    matched: set[str] = set()
    verdicts: list[str] = []
    for finding in findings:
        locs = finding.get("locations") or []
        cwe = finding.get("cwe")
        verdict = "unresolved:out_of_scope"
        for defect in defects:
            anchors = {_key(a) for a in defect["anchors"]}
            if not any(_key(loc) in anchors for loc in locs):
                continue
            if cwe not in defect["accepted_cwes"]:
                verdict = "unresolved:class_mismatch"
            elif defect["defect_id"] in matched:
                verdict = "duplicate"
            else:
                matched.add(defect["defect_id"])
                verdict = "confirmed"
            break
        else:
            on_focal = variant == focal["variant"] and any(
                _key(loc) == _key(focal["anchor"]) for loc in locs
            )
            if on_focal or (locs and all(_in_scope(loc, scope) for loc in locs)):
                verdict = "refuted"
        verdicts.append(verdict)
    return verdicts


@scorer(metrics=[mean()])
def findings_matcher() -> Any:
    async def score(state: TaskState, target: Target) -> Score:
        capture = state.store.get(CAPTURE_KEY) or {"status": "no_submission"}
        meta = state.metadata
        if capture["status"] != "captured":
            return Score(value=0, answer="no_submission", metadata={"capture": capture})
        labels = json.loads((ORACLES / meta["task_id"] / "labels.json").read_text())
        try:
            findings = json.loads(capture["text"])
            if not isinstance(findings, list):
                raise ValueError("findings.json must be a JSON array")
        except ValueError as exc:
            return Score(value=0, answer="invalid_submission", explanation=str(exc))
        verdicts = match(findings, labels, meta["variant"])
        disposition = "completed_with_findings" if findings else "completed_no_findings"
        return Score(
            value=verdicts.count("confirmed"),
            answer=disposition,
            metadata={"verdicts": verdicts, "findings_sha256": capture["sha256"]},
        )

    return score
