# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Re-score a saved spike log offline and compare with the live verdicts.

    uv run --extra inspect python spikes/inspect_day2/rescore.py <log.eval>

No sandbox exists at re-score time, so this only works because the live run
captured ``findings.json`` into the sample store (see ``scorer.py``).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from inspect_ai.log import read_eval_log
from inspect_ai.scorer import Scorer

sys.path.insert(0, str(Path(__file__).parent))

from scorer import findings_matcher


def _verdicts(samples: list[Any], name: str) -> dict[str, Any]:
    return {
        str(s.id): (s.scores[name].metadata or {}).get("verdicts", s.scores[name].answer)
        for s in samples
        if s.scores and name in s.scores
    }


def rescore(path: str) -> tuple[dict[str, Any], dict[str, Any]]:
    from inspect_ai import score

    log = read_eval_log(path)
    live = _verdicts(log.samples or [], "findings_matcher")
    scorer: Scorer = findings_matcher()
    rescored = score(log, [scorer], action="overwrite")
    again = _verdicts(rescored.samples or [], "findings_matcher")
    return live, again


if __name__ == "__main__":
    live, again = rescore(sys.argv[1])
    print("live:    ", live)
    print("rescored:", again)
    sys.exit(0 if live == again and live else 1)
