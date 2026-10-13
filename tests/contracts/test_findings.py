# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Finding contract: the shape rules of scoring.md §2.1 and §4.1 (N1-N4).

Checks that need the agent view (the file exists, lines within the file) are
the matcher's job (AP-007) and are tested there.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from aureproof.contracts import Finding, Location, Role

ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "conformance" / "contracts" / "v0.1" / "finding"


def _finding(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "cwe": 862,
        "locations": [{"file": "docstore/service.py", "symbol": "delete_document"}],
        "description": "No ownership check.",
    }
    return {**base, **overrides}


def test_minimal_finding_defaults() -> None:
    f = Finding.model_validate(_finding())
    assert f.cwe == 862
    loc = f.locations[0]
    assert loc.role is Role.SITE
    assert loc.start_line is None and loc.end_line is None


@pytest.mark.parametrize("cwe", ["CWE-89", "cwe-89", "Cwe-89", 89])
def test_cwe_normalizes_to_int(cwe: object) -> None:  # N3
    assert Finding.model_validate(_finding(cwe=cwe)).cwe == 89


@pytest.mark.parametrize("cwe", [0, -1, True, 89.0, "89", "CWE-", "CWE-89a", "SQLi", None])
def test_bad_cwe_is_invalid(cwe: object) -> None:  # N3
    with pytest.raises(ValidationError):
        Finding.model_validate(_finding(cwe=cwe))


def test_end_line_defaults_to_start_line() -> None:  # N2
    loc = Location.model_validate({"file": "a.py", "start_line": 7})
    assert loc.end_line == 7


def test_leading_dot_slash_is_stripped() -> None:  # N1
    assert Location.model_validate({"file": "./a/b.py", "symbol": "f"}).file == "a/b.py"


@pytest.mark.parametrize(
    "location",
    [
        {"file": "/etc/passwd", "symbol": "f"},  # absolute
        {"file": "a/../../b.py", "symbol": "f"},  # leaves the workspace
        {"file": "a\\b.py", "symbol": "f"},  # backslash
        {"file": "", "symbol": "f"},
        {"file": "a.py"},  # neither symbol nor start_line
        {"file": "a.py", "end_line": 3},  # end without start
        {"file": "a.py", "start_line": 0},
        {"file": "a.py", "start_line": 5, "end_line": 4},
        {"file": "a.py", "start_line": "5"},  # strings are not coerced
        {"file": "a.py", "symbol": ""},
        {"file": "a.py", "symbol": "f", "role": "caller"},
        {"file": "a.py", "symbol": "f", "extra": 1},
    ],
)
def test_invalid_locations(location: dict[str, Any]) -> None:  # N1, N2, N4
    with pytest.raises(ValidationError):
        Location.model_validate(location)


@pytest.mark.parametrize(
    "overrides",
    [
        {"locations": []},
        {"locations": [{"file": "a.py", "symbol": "f"}] * 5},  # max_locations = 4
        {"description": ""},
        {"description": "x" * 4001},
        {"description": 7},
        {"locations": "a.py"},
    ],
)
def test_invalid_findings(overrides: dict[str, Any]) -> None:  # N4
    with pytest.raises(ValidationError):
        Finding.model_validate(_finding(**overrides))


@pytest.mark.parametrize("missing", ["cwe", "locations", "description"])
def test_required_fields(missing: str) -> None:  # N4
    raw = _finding()
    del raw[missing]
    with pytest.raises(ValidationError):
        Finding.model_validate(raw)


def test_unknown_finding_fields_are_preserved_as_evidence() -> None:
    f = Finding.model_validate(_finding(confidence="high", finding_id="a1"))
    assert f.finding_id == "a1"
    assert f.model_extra == {"confidence": "high"}


def test_findings_are_immutable() -> None:
    f = Finding.model_validate(_finding())
    with pytest.raises(ValidationError):
        f.cwe = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    "path", sorted(VECTORS.glob("*/*.json")), ids=lambda p: f"{p.parent.name}/{p.stem}"
)
def test_conformance_vector(path: Path) -> None:
    vector = json.loads(path.read_text(encoding="utf-8"))
    if path.parent.name == "valid":
        Finding.model_validate(vector["instance"])
    else:
        with pytest.raises(ValidationError):
            Finding.model_validate(vector["instance"])


def test_there_are_conformance_vectors() -> None:
    assert len(list(VECTORS.glob("valid/*.json"))) >= 3
    assert len(list(VECTORS.glob("invalid/*.json"))) >= 5


# Rules the model enforces but JSON Schema cannot express: end_line >= start_line,
# and integral floats (JSON Schema 2020-12 counts 862.0 as an integer; the model
# rejects it so that a float never silently becomes a CWE or a line number).
MODEL_ONLY = {"reversed-lines", "cwe-float"}


@pytest.mark.parametrize(
    "path", sorted(VECTORS.glob("*/*.json")), ids=lambda p: f"{p.parent.name}/{p.stem}"
)
def test_exported_schema_agrees_with_the_model(path: Path) -> None:
    """The published schema accepts every valid vector and rejects the invalid ones."""
    from jsonschema import Draft202012Validator

    schema = json.loads(
        (ROOT / "specs" / "contracts" / "v0.1" / "finding.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    errors = list(
        Draft202012Validator(schema).iter_errors(json.loads(path.read_text())["instance"])
    )
    if path.parent.name == "valid":
        assert not errors
    elif path.stem not in MODEL_ONLY:
        assert errors, "schema accepted an invalid vector"
