# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Keep docs/fault-qualification.md honest (issue #55): every cited test exists."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "fault-qualification.md"


def _cited() -> list[tuple[str, str]]:
    cited = []
    for line in DOC.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or "`tests/" not in line:
            continue
        current = None
        for path, name in re.findall(r"`(tests/[\w/]+\.py)?::(\w+)`", line.split("|")[-2]):
            current = path or current
            assert current, f"a citation without a file: {line}"
            cited.append((current, name))
    return cited


def test_every_scenario_cites_tests_that_exist() -> None:
    cited = _cited()
    assert len(cited) >= 20
    for path, name in cited:
        tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
        assert any(isinstance(n, ast.FunctionDef) and n.name == name for n in ast.walk(tree)), (
            f"{path}::{name} does not exist"
        )
