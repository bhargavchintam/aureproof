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

Verdicts come from ``aureproof.scoring`` (AP-007) via ``grading.py``; the spike
no longer carries a matcher of its own (issue #34).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

from inspect_ai.scorer import Score, Target, mean, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import sandbox, store

sys.path.insert(0, str(Path(__file__).parent))

from grading import grade

CAPTURE_KEY = "aureproof_capture"
FINDINGS_FILE = "findings.json"


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


@scorer(metrics=[mean()])
def findings_matcher() -> Any:
    """Grades only the captured bytes, through the canonical core (never the sandbox)."""

    async def score(state: TaskState, target: Target) -> Score:
        meta = state.metadata
        graded = grade(
            state.store.get(CAPTURE_KEY), task_id=meta["task_id"], variant=meta["variant"]
        )
        return Score(value=len(graded["credited"]), answer=graded["disposition"], metadata=graded)

    return score
