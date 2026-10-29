# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Fuzz the strict, bounded JSON loader that reads every untrusted record (issue #35).

The only allowed failure is JsonInputError; anything else is a bug.
"""

from __future__ import annotations

import contextlib
import sys

import atheris

with atheris.instrument_imports():
    from aureproof.contracts.strict_json import JsonInputError, loads_strict


def test_one_input(data: bytes) -> None:
    for i_json in (False, True):
        with contextlib.suppress(JsonInputError):
            loads_strict(data, i_json=i_json)


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()
