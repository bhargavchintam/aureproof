# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Fuzz the parser of agent-written findings.json bytes (scoring.md §3).

It must never raise: every input becomes a parsed submission with a status.
"""

from __future__ import annotations

import sys

import atheris

with atheris.instrument_imports():
    from aureproof.scoring.submission import parse_submission


def test_one_input(data: bytes) -> None:
    parsed = parse_submission(data)
    assert parsed.status is not None


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()
