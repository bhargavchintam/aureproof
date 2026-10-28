# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Adjudication through the gate and the CLI (issue #51)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from typer.testing import CliRunner

from aureproof.bundle.canonical import digest_ref
from aureproof.bundle.compare import GateError, compare
from aureproof.cli.main import app
from aureproof.contracts.adjudication import Adjudication
from aureproof.contracts.decision import DecisionProtocol
from aureproof.storage import write_bundle

ROOT = Path(__file__).resolve().parents[2]
cli = CliRunner()


def _generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gate", ROOT / "scripts/make_gate_examples.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def evidence() -> tuple[DecisionProtocol, dict[str, bytes], dict[str, bytes]]:
    """A: 1/2 per cluster. B: one hit and one class mismatch per cluster (1/2 before
    adjudication, 2/2 once the mismatches are confirmed)."""
    g = _generator()
    wrong_class = {**g.HIT, "cwe": 79}
    plan = [(g.HALF, ([g.HIT, wrong_class], []))] * 8
    thrs = {t: g._thr(t) for t in g.TASKS}
    protocol = g._protocol("adjudication", thrs)
    return protocol, g._bundle("A", protocol, thrs, plan), g._bundle("B", protocol, thrs, plan)


def _confirm_all(files: dict[str, bytes], who: str = "ana", role: str = "primary") -> list[Any]:
    seal = digest_ref(files["seal.intoto.json"])
    episodes = json.loads(files["episodes.json"])
    return [
        Adjudication.model_validate(
            {
                "bundle_seal": seal,
                "finding": {"episode_id": e["episode_id"], "finding_index": 1},
                "original_verdict": "unresolved:class_mismatch",
                "adjudicator": who,
                "role": role,
                "decision": "confirmed",
                "rationale": "CWE-79 named, but the code is the labeled SQL injection",
                "timestamp": "2026-10-28T12:00:00Z",
                "dataset_revision_before": "0.1.0",
                "dataset_revision_after": "0.1.0",
            }
        )
        for e in episodes
        if e["variant"] == "vulnerable"
    ]


def test_unadjudicated_findings_keep_the_gate_inconclusive(evidence: Any) -> None:
    protocol, a, b = evidence
    decision = compare(protocol, a, b).decision
    assert (decision.provisional_outcome, decision.outcome) == ("pass", "inconclusive")
    assert "not adjudicated" in decision.reason


def test_adjudicated_findings_count_and_the_gate_decides(evidence: Any) -> None:
    protocol, a, b = evidence
    decision = compare(protocol, a, b, adjudications_b=_confirm_all(b)).decision
    assert decision.outcome == "pass"
    assert {row.b_confirmed for row in decision.cluster_table} == {2}
    assert {row.b_unresolved for row in decision.cluster_table} == {0}
    partial = _confirm_all(b)[:7]  # one cluster still unresolved
    assert compare(protocol, a, b, adjudications_b=partial).decision.outcome == "inconclusive"


def test_records_for_the_other_bundle_fail_closed(evidence: Any) -> None:
    protocol, a, b = evidence
    with pytest.raises(GateError, match="made for another bundle"):
        compare(protocol, a, b, adjudications_a=_confirm_all(b))


def test_cli_queue_record_report_compare(evidence: Any, tmp_path: Path) -> None:
    protocol, a, b = evidence
    write_bundle(a, tmp_path / "a")
    write_bundle(b, tmp_path / "b")
    (tmp_path / "protocol.json").write_text(protocol.model_dump_json())
    records = tmp_path / "b.adjudications.jsonl"

    queued = cli.invoke(app, ["adjudicate", "queue", str(tmp_path / "b")])
    assert queued.exit_code == 0 and "8 unresolved finding(s)" in queued.output
    episodes = [e for e in json.loads(b["episodes.json"]) if e["variant"] == "vulnerable"]
    for n, e in enumerate(episodes):
        for who, role in [("ana", "primary")] + ([("ben", "second")] if n < 2 else []):
            args = ["adjudicate", "record", str(tmp_path / "b"), "--episode", e["episode_id"]]
            args += ["--finding", "1", "--decision", "confirmed", "--adjudicator", who]
            args += ["--role", role, "--rationale", "it is the labeled defect"]
            args += ["--revision", "0.1.0", "--out", str(records)]
            assert cli.invoke(app, args).exit_code == 0
    assert len(records.read_text().splitlines()) == 10

    report = cli.invoke(
        app,
        ["adjudicate", "report", str(tmp_path / "b"), "--adjudications", str(records), "--json"],
    )
    data = json.loads(report.output)
    assert report.exit_code == 0, report.output
    assert data["statuses"] == {"decided": 8} and data["coverage_ok"] is True
    assert data["double_adjudicated"] == 2 and data["kappa"] is None  # all agree in one category
    assert data["post_adjudication"]["strict_confirmed_yield"] == "16/16"

    base = ["compare", "--protocol", str(tmp_path / "protocol.json")]
    base += ["--a", str(tmp_path / "a"), "--b", str(tmp_path / "b")]
    assert cli.invoke(app, base).exit_code == 3
    assert cli.invoke(app, [*base, "--adjudications-b", str(records)]).exit_code == 0


def test_cli_refuses_a_finding_that_is_not_unresolved(evidence: Any, tmp_path: Path) -> None:
    _, _, b = evidence
    write_bundle(b, tmp_path / "b")
    episode = json.loads(b["episodes.json"])[0]["episode_id"]
    args = ["adjudicate", "record", str(tmp_path / "b"), "--episode", episode, "--finding", "0"]
    args += ["--decision", "confirmed", "--adjudicator", "ana", "--rationale", "x"]
    args += ["--revision", "0.1.0", "--out", str(tmp_path / "r.jsonl")]
    result = cli.invoke(app, args)
    assert result.exit_code == 2 and "is not an unresolved finding" in result.output
    assert not (tmp_path / "r.jsonl").exists()
