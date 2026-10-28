# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Keep docs/ABC.md honest (issue #61): every cited repository path exists."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs" / "ABC.md").read_text(encoding="utf-8")
STATUSES = ("met", "partly met", "not met", "n/a", "met (by design)")


def test_every_cited_path_exists() -> None:
    cited = set(re.findall(r"`((?:docs|specs|fixtures|tests|src|runners)/[^`*:\s]+)", DOC))
    assert len(cited) >= 10
    for path in sorted(cited):
        target = path if not path.startswith("runners/") else f"src/aureproof/{path}"
        target = target.split("::")[0]
        matches = list(ROOT.glob(target)) if "*" in target else [ROOT / target]
        assert matches and all(m.exists() for m in matches), path


def test_every_row_has_a_status() -> None:
    rows = [line for line in DOC.splitlines() if re.match(r"\| I{1,3}\.", line)]
    assert len(rows) >= 30
    for row in rows:
        assert row.split("|")[3].strip() in STATUSES, row
