# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Architecture guardrails (plan v2 §3.2).

`lint-imports` is the authoritative check (run in CI and pre-commit). This test
is a fast local backstop: it imports each pure-core package and asserts no
adapter or CLI module was pulled in as a side effect.
"""

from __future__ import annotations

import sys

PURE_CORE = ("contracts", "scoring", "stats", "bundle")
FORBIDDEN = ("runners", "importers", "exporters", "oracles", "cli")


def test_pure_core_imports_without_adapters() -> None:
    for name in FORBIDDEN:
        sys.modules.pop(f"aureproof.{name}", None)

    for pkg in PURE_CORE:
        __import__(f"aureproof.{pkg}")

    leaked = [f"aureproof.{n}" for n in FORBIDDEN if f"aureproof.{n}" in sys.modules]
    assert not leaked, f"pure core pulled in adapter/CLI modules: {leaked}"
