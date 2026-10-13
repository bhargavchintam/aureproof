# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""SARIF 2.1.0 mapping (plan §5.2) and the exported JSON Schemas (AP-004)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from aureproof.contracts import Finding, Location, Role
from aureproof.contracts.sarif import SARIF_VERSION, findings_from_sarif, findings_to_sarif
from aureproof.contracts.schema import SCHEMA_DIR, export_schemas

ROOT = Path(__file__).resolve().parents[2]

FINDINGS = [
    Finding.model_validate(
        {
            "finding_id": "f-1",
            "cwe": 862,
            "locations": [
                {
                    "file": "docstore/service.py",
                    "symbol": "delete_document",
                    "start_line": 60,
                    "end_line": 63,
                    "role": "site",
                },
                {"file": "docstore/api.py", "symbol": "handle_request", "role": "source"},
            ],
            "description": "Any actor can delete any document.",
        }
    ),
    Finding.model_validate(
        {"cwe": 639, "locations": [{"file": "a.py", "start_line": 3}], "description": "x"}
    ),
]


def test_sarif_document_shape() -> None:
    doc = findings_to_sarif(FINDINGS, tool_name="aureproof-test", tool_version="0.0.0")
    assert doc["version"] == SARIF_VERSION == "2.1.0"
    [run] = doc["runs"]
    first = run["results"][0]
    assert first["ruleId"] == "CWE-862"
    assert first["properties"]["finding_id"] == "f-1" and "guid" not in first
    assert first["message"]["text"] == "Any actor can delete any document."
    loc = first["locations"][0]
    assert loc["physicalLocation"]["artifactLocation"]["uri"] == "docstore/service.py"
    assert loc["physicalLocation"]["region"] == {"startLine": 60, "endLine": 63}
    assert loc["logicalLocations"] == [{"name": "delete_document"}]
    assert first["locations"][1]["properties"]["role"] == "source"
    assert "region" not in first["locations"][1]["physicalLocation"]


def test_sarif_round_trip_preserves_findings() -> None:
    doc = findings_to_sarif(FINDINGS, tool_name="t", tool_version="1")
    back = [Finding.model_validate(raw) for raw in findings_from_sarif(json.loads(json.dumps(doc)))]
    assert back == FINDINGS


def test_import_reads_cwe_from_taxa_or_rule_tags() -> None:
    """Third-party tools (CodeQL, Semgrep, Bandit) put CWEs in different places."""
    doc: dict[str, Any] = {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "scanner",
                        "rules": [
                            {
                                "id": "py/sql-injection",
                                "properties": {"tags": ["security", "external/cwe/cwe-089"]},
                            },
                            {"id": "B602", "properties": {"tags": ["CWE-78"]}},
                        ],
                    }
                },
                "results": [
                    {
                        "ruleId": "py/sql-injection",
                        "ruleIndex": 0,
                        "message": {"text": "sqli"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "a.py"},
                                    "region": {"startLine": 4},
                                }
                            }
                        ],
                    },
                    {
                        "ruleId": "B602",
                        "message": {"text": "shell"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "b.py"},
                                    "region": {"startLine": 9},
                                }
                            }
                        ],
                    },
                    {
                        "ruleId": "custom",
                        "taxa": [{"id": "22", "toolComponent": {"name": "CWE"}}],
                        "message": {"text": "path"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "c.py"},
                                    "region": {"startLine": 1},
                                }
                            }
                        ],
                    },
                    {
                        "ruleId": "no-cwe",
                        "message": {"text": "style"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "d.py"},
                                    "region": {"startLine": 2},
                                }
                            }
                        ],
                    },
                ],
            }
        ],
    }
    raws = findings_from_sarif(doc)
    assert [r.get("cwe") for r in raws] == [89, 78, 22, None]
    assert [Finding.model_validate(r).cwe for r in raws[:3]] == [89, 78, 22]
    assert raws[1]["locations"][0] == {
        "file": "b.py",
        "start_line": 9,
        "end_line": 9,
        "role": "site",
    }


def test_import_rejects_other_sarif_versions() -> None:
    with pytest.raises(ValueError, match=r"2\.1\.0"):
        findings_from_sarif({"version": "2.0.0", "runs": []})


_symbols = st.from_regex(
    r"[A-Za-z_][A-Za-z0-9_]{0,10}(\.[A-Za-z_][A-Za-z0-9_]{0,10}){0,2}", fullmatch=True
)
_paths = st.from_regex(r"[a-z]{1,8}(/[a-z]{1,8}){0,3}\.py", fullmatch=True)


@st.composite
def _locations(draw: st.DrawFn) -> Location:
    start = draw(st.none() | st.integers(1, 5000))
    symbol = draw(_symbols if start is None else st.none() | _symbols)
    end = None if start is None else draw(st.integers(start, start + 200))
    return Location(
        file=draw(_paths),
        symbol=symbol,
        start_line=start,
        end_line=end,
        role=draw(st.sampled_from(list(Role))),
    )


@given(
    st.lists(
        st.builds(
            Finding,
            cwe=st.integers(1, 2000),
            locations=st.lists(_locations(), min_size=1, max_size=4),
            description=st.text(min_size=1, max_size=200),
            finding_id=st.none() | st.text(min_size=1, max_size=20),
        ),
        max_size=8,
    )
)
def test_sarif_round_trip_property(findings: list[Finding]) -> None:
    doc = findings_to_sarif(findings, tool_name="t", tool_version="1")
    back = [Finding.model_validate(r) for r in findings_from_sarif(json.loads(json.dumps(doc)))]
    assert back == findings


def test_committed_schemas_match_the_models() -> None:
    """Run `uv run python scripts/export_schemas.py` after changing a contract."""
    generated = export_schemas()
    on_disk = {
        p.stem.removesuffix(".schema"): json.loads(p.read_text(encoding="utf-8"))
        for p in (ROOT / SCHEMA_DIR).glob("*.schema.json")
    }
    assert on_disk == generated


def test_schemas_declare_draft_2020_12() -> None:
    for name, schema in export_schemas().items():
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema", name
