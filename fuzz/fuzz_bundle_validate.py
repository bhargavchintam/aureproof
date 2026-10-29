# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Fuzz evidence-bundle validation (V1-V6) with hostile member bytes (issue #35).

Validation reports problems; it must never raise.
"""

from __future__ import annotations

import sys

import atheris

with atheris.instrument_imports():
    from aureproof.bundle import validate

NAMES = ("manifest.json", "seal.intoto.json", "journal.jsonl", "verdicts.json", "metrics.json")


def test_one_input(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    files = {}
    for name in NAMES:
        if fdp.ConsumeBool():
            files[name] = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 4096))
    validate(files)


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()
