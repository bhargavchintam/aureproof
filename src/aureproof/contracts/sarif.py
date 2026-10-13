# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Map findings to and from SARIF 2.1.0 (plan v2 §5.2). Pure dict transforms.

Export is lossless for findings, so baselines and other tools can consume
Aureproof findings. Import returns *raw* finding dicts that then go through the
same validation as agent output; a SARIF result without a recoverable CWE
simply has no ``cwe`` and becomes an ``invalid`` verdict when scored.

The agent's ``finding_id`` is stored in ``properties.finding_id`` rather than
``result.guid``, because SARIF requires ``guid`` to be a GUID.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from aureproof.contracts.findings import Finding

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
INFORMATION_URI = "https://github.com/bhargavchintam/aureproof"
_RESERVED = {"cwe", "locations", "description", "finding_id"}
_CWE_ID = re.compile(r"(?i)^cwe-0*([1-9][0-9]*)$")
_CWE_TAG = re.compile(r"(?i)cwe[-/]0*([1-9][0-9]*)$")


def _result(finding: Finding) -> dict[str, Any]:
    locations = []
    for loc in finding.locations:
        physical: dict[str, Any] = {"artifactLocation": {"uri": loc.file}}
        if loc.start_line is not None:
            physical["region"] = {"startLine": loc.start_line, "endLine": loc.end_line}
        entry: dict[str, Any] = {"physicalLocation": physical, "properties": {"role": loc.role}}
        if loc.symbol is not None:
            entry["logicalLocations"] = [{"name": loc.symbol}]
        locations.append(entry)
    properties = dict(finding.model_extra or {})
    if finding.finding_id is not None:
        properties["finding_id"] = finding.finding_id
    result: dict[str, Any] = {
        "ruleId": f"CWE-{finding.cwe}",
        "message": {"text": finding.description},
        "taxa": [{"id": str(finding.cwe), "toolComponent": {"name": "CWE"}}],
        "locations": locations,
    }
    if properties:
        result["properties"] = properties
    return result


def findings_to_sarif(
    findings: Iterable[Finding], *, tool_name: str, tool_version: str
) -> dict[str, Any]:
    """One SARIF log with one run holding every finding, in order."""
    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": tool_name,
                        "version": tool_version,
                        "informationUri": INFORMATION_URI,
                    }
                },
                "taxonomies": [{"name": "CWE", "organization": "MITRE"}],
                "results": [_result(f) for f in findings],
            }
        ],
    }


def _cwe(result: Mapping[str, Any], rules: list[Any]) -> int | None:
    rule_id = str(result.get("ruleId", ""))
    if m := _CWE_ID.match(rule_id):
        return int(m.group(1))
    for taxon in result.get("taxa") or []:
        component = str((taxon.get("toolComponent") or {}).get("name", ""))
        if component.upper() == "CWE":
            taxon_id = str(taxon.get("id", ""))
            if taxon_id.isdigit() and int(taxon_id) > 0:
                return int(taxon_id)
            if m := _CWE_ID.match(taxon_id):
                return int(m.group(1))
    rule: Mapping[str, Any] | None = None
    index = result.get("ruleIndex")
    if isinstance(index, int) and 0 <= index < len(rules):
        rule = rules[index]
    else:
        rule = next((r for r in rules if r.get("id") == rule_id), None)
    for tag in ((rule or {}).get("properties") or {}).get("tags") or []:
        if m := _CWE_TAG.search(str(tag)):
            return int(m.group(1))
    return None


def _location(entry: Mapping[str, Any]) -> dict[str, Any]:
    physical = entry.get("physicalLocation") or {}
    raw: dict[str, Any] = {"file": (physical.get("artifactLocation") or {}).get("uri")}
    logical = entry.get("logicalLocations") or []
    if logical:
        symbol = logical[0].get("name") or logical[0].get("fullyQualifiedName")
        if symbol is not None:
            raw["symbol"] = symbol
    region = physical.get("region") or {}
    if "startLine" in region:
        raw["start_line"] = region["startLine"]
        raw["end_line"] = region.get("endLine", region["startLine"])
    raw["role"] = (entry.get("properties") or {}).get("role", "site")
    return raw


def findings_from_sarif(log: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Raw finding dicts, in run and result order, for normal validation."""
    if log.get("version") != SARIF_VERSION:
        raise ValueError(f"only SARIF {SARIF_VERSION} is supported, got {log.get('version')!r}")
    raws: list[dict[str, Any]] = []
    for run in log.get("runs") or []:
        rules = ((run.get("tool") or {}).get("driver") or {}).get("rules") or []
        for result in run.get("results") or []:
            properties = dict(result.get("properties") or {})
            raw: dict[str, Any] = {k: v for k, v in properties.items() if k not in _RESERVED}
            cwe = _cwe(result, rules)
            if cwe is not None:
                raw["cwe"] = cwe
            raw["locations"] = [_location(e) for e in result.get("locations") or []]
            raw["description"] = (result.get("message") or {}).get("text", "")
            if "finding_id" in properties:
                raw["finding_id"] = properties["finding_id"]
            raws.append(raw)
    return raws
