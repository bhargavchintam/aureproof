# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Keep docs/threat-model.md honest (issue #17).

Every cited test must exist. A control marked "tested (CI)" may cite only tests
that run in the required CI job, not the optional Docker lane. Pending or
partial controls must name the issue that delivers the rest.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "threat-model.md"
LANE_ONLY = ("tests/integration/",)
STATUSES = {"tested (CI)", "tested (lane)", "partial", "pending"}


def _rows() -> list[dict[str, str]]:
    rows = []
    for line in DOC.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 7 and re.fullmatch(r"T-[A-Z]+-\d+", cells[0]):
            rows.append(
                dict(
                    zip(
                        ("id", "stride", "threat", "control", "status", "evidence", "limits"),
                        cells,
                        strict=True,
                    )
                )
            )
    return rows


def _defined(path: str, name: str) -> bool:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    return any(isinstance(n, ast.FunctionDef) and n.name == name for n in ast.walk(tree))


ROWS = _rows()


def test_matrix_covers_every_stride_category() -> None:
    assert {r["stride"] for r in ROWS} >= {
        "Spoofing",
        "Tampering",
        "Repudiation",
        "Information disclosure",
        "Denial of service",
        "Elevation of privilege",
    }
    assert len({r["id"] for r in ROWS}) == len(ROWS)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["id"])
def test_row_evidence_is_real_and_honest(row: dict[str, str]) -> None:
    assert row["status"] in STATUSES, row["status"]
    cited = re.findall(r"`(tests/[\w/]+\.py)::(\w+)`", row["evidence"])
    for path, name in cited:
        assert (ROOT / path).exists(), path
        assert _defined(path, name), f"{path}::{name} does not exist"
    if row["status"] == "tested (CI)":
        assert cited, "a tested control cites at least one test"
        assert not [p for p, _ in cited if p.startswith(LANE_ONLY)], (
            "lane tests are not CI evidence"
        )
    if row["status"] == "tested (lane)":
        assert any(p.startswith(LANE_ONLY) for p, _ in cited)
    if row["status"] in {"partial", "pending"}:
        assert re.search(r"#\d+", row["limits"]), "name the issue that delivers the rest"
