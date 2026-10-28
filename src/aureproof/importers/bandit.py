# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Bandit as a static baseline: pinned run, SARIF import, declared losses (issue #44).

Adapter (process I/O). Bandit runs from the variant root, so its SARIF URIs are
workspace-relative like an agent's. The SARIF goes through the same
``findings_from_sarif`` import, finding validation and matcher as agent output;
nothing about scoring is Bandit-specific.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aureproof.bundle.canonical import digest_ref
from aureproof.contracts.sarif import findings_from_sarif

BANDIT_VERSION = "1.9.4"
BANDIT_ARGS = ("-q", "-r", ".", "-f", "sarif")
BANDIT_TIMEOUT_S = 120
# What the mapping cannot carry. Every Bandit finding is affected by the first two.
MAPPING_LOSSES = (
    "no symbol: Bandit reports lines, so findings match by line range only",
    "no data-flow role: every location is a site",
    "severity and confidence are kept as extra fields and never scored",
    "a rule without a CWE tag gives a finding without a CWE, graded invalid",
)


@dataclass(frozen=True)
class BanditImport:
    findings: list[dict[str, Any]]
    tool_version: str
    without_cwe: int  # results the mapping could not give a CWE


def system_identity() -> str:
    """The baseline as a system: tool, pinned version, arguments."""
    return digest_ref({"system": "bandit", "version": BANDIT_VERSION, "args": list(BANDIT_ARGS)})


def import_sarif(log: Mapping[str, Any]) -> BanditImport:
    """Bandit SARIF to raw findings; refuses another tool or an unpinned version."""
    runs = log.get("runs") or []
    driver = ((runs[0].get("tool") or {}).get("driver") or {}) if runs else {}
    if driver.get("name") != "Bandit":
        raise ValueError(f"not a Bandit log: tool {driver.get('name')!r}")
    if driver.get("version") != BANDIT_VERSION:
        raise ValueError(f"Bandit {driver.get('version')!r} is not the pinned {BANDIT_VERSION}")
    findings = findings_from_sarif(log)
    return BanditImport(
        findings=findings,
        tool_version=BANDIT_VERSION,
        without_cwe=sum("cwe" not in f for f in findings),
    )


def run(variant_dir: Path) -> dict[str, Any]:
    """Run the pinned Bandit on one variant and return its SARIF log."""
    out = subprocess.run(
        [sys.executable, "-m", "bandit", *BANDIT_ARGS],
        cwd=variant_dir,
        capture_output=True,
        text=True,
        timeout=BANDIT_TIMEOUT_S,
        check=False,
    )
    # Bandit exits 1 when it reports issues; anything else is a failed run.
    if out.returncode not in (0, 1):
        raise RuntimeError(f"bandit failed ({out.returncode}): {out.stderr[-500:]}")
    log: dict[str, Any] = json.loads(out.stdout)
    return log
