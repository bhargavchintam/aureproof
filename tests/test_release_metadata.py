# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Release metadata agrees with itself (issue #56): versions, license, pins."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
VERSION = PYPROJECT["project"]["version"]
CITATION = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
ZENODO = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
COMPAT = (ROOT / "specs" / "COMPATIBILITY.md").read_text(encoding="utf-8")


def test_package_citation_and_changelog_versions_agree() -> None:
    assert re.search(rf'^version: "{re.escape(VERSION)}"$', CITATION, re.M)
    assert "## [Unreleased]" in CHANGELOG
    if VERSION != "0.0.0":  # a released version must have its own changelog section
        assert f"## [{VERSION}]" in CHANGELOG


def test_license_and_title_agree_across_metadata() -> None:
    assert PYPROJECT["project"]["license"] in ("Apache-2.0", {"text": "Apache-2.0"})
    assert "license: Apache-2.0" in CITATION and ZENODO["license"] == "Apache-2.0"
    title = re.search(r'^title: "(.+)"$', CITATION, re.M)
    assert title is not None and ZENODO["title"] == title.group(1)


def _pin(component: str) -> str:
    row = next(line for line in COMPAT.splitlines() if line.startswith(f"| {component} |"))
    return row.split("|")[2].strip().strip("`").split("`")[0]


def test_documented_pins_match_the_real_pins() -> None:
    deps = [*PYPROJECT["project"]["optional-dependencies"]["inspect"]]
    deps += PYPROJECT["project"]["optional-dependencies"]["sign"]
    deps += PYPROJECT["project"]["optional-dependencies"]["baseline"]
    pins = {d.split("==")[0]: d.split("==")[1] for d in deps if "==" in d}
    for name in ("inspect-ai", "inspect-swe", "sigstore", "bandit[sarif]"):
        assert _pin(name) == pins[name], name
    assert _pin("Python") == PYPROJECT["project"]["requires-python"]
    runner = (ROOT / "src/aureproof/runners/inspect_runner.py").read_text(encoding="utf-8")
    assert f'claude_code_version: str = "{_pin("Claude Code")}"' in runner
    exporter = (ROOT / "src/aureproof/exporters/eee.py").read_text(encoding="utf-8")
    assert f'EEE_VERSION = "{_pin("Every Eval Ever")}"' in exporter
    croissant = json.loads((ROOT / "fixtures/croissant.json").read_text(encoding="utf-8"))
    assert croissant["conformsTo"].endswith("/" + _pin("Croissant"))
    for workflow in (ROOT / ".github/workflows").glob("*.yml"):
        for found in re.findall(r'version: "(\d+\.\d+\.\d+)"', workflow.read_text("utf-8")):
            assert found == _pin("uv"), workflow.name
