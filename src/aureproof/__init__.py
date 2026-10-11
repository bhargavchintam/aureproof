# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Aureproof: an open-source integrity layer for AI-agent evaluations.

Public API is intentionally empty on the Day-1 scaffold. Component packages
(`contracts`, `scoring`, `stats`, `bundle`, and the `runners`/`importers`/
`exporters`/`oracles` adapters) are filled in during milestones M1-M2; see
``docs/aureproof-plan-v2.md``.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("aureproof")
except PackageNotFoundError:  # pragma: no cover - only in a non-installed tree
    __version__ = "0.0.0"

__all__ = ["__version__"]
