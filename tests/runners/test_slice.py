# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""A protocol-bound run sealed into one bundle (issue #47); fake runner, no Inspect."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aureproof.bundle import validate
from aureproof.bundle.run import rescore
from aureproof.contracts import SystemSpec
from aureproof.contracts.decision import CohortTask, Configurations, DecisionProtocol
from aureproof.contracts.specs import content_identity
from aureproof.contracts.thr import TaskHealthRecord
from aureproof.oracles.calibration import calibrate, task_spec
from aureproof.runners.port import AttemptRequest, AttemptResult, SampleFacts, classify
from aureproof.runners.slice import SliceError, plan, run_slice, thr_digest

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = SystemSpec.model_validate(
    json.loads(
        (ROOT / "conformance/contracts/v0.1/system-spec/valid/reference-react.json").read_text()
    )["instance"]
)
TOOLS = ["bash", "submit"]
FINDING = [
    {
        "cwe": 862,
        "description": "no ownership check",
        "locations": [{"file": "docstore/service.py", "symbol": "delete_document"}],
    }
]


class SliceRunner:
    """Reports a finding on authz-001 and nothing elsewhere."""

    def __init__(self) -> None:
        self.seen: list[str] = []

    def system_spec(self) -> SystemSpec:
        return SYSTEM

    def run_attempt(self, request: AttemptRequest) -> AttemptResult:
        self.seen.append(request.attempt_id)
        found = FINDING if request.task.task_id == "authz-001" else []
        facts = SampleFacts(
            log_digest="sha256:" + "b" * 64,
            model_requests=2,
            request_ids=[f"req-{len(self.seen)}"],
            offered_tools=frozenset(TOOLS),
            capture_status="captured",
            submission=json.dumps(found).encode(),
        )
        return classify(facts, declared_tools=TOOLS)


@pytest.fixture(scope="module")
def thrs() -> dict[str, TaskHealthRecord]:
    return {t: calibrate(ROOT, t) for t in ("authz-001", "path-001")}


def protocol(thrs: dict[str, TaskHealthRecord], **kw: Any) -> DecisionProtocol:
    fields: dict[str, Any] = {
        "protocol_version": "0.1",
        "name": "m2-slice-test",
        "cohort": [
            CohortTask(
                task_identity=task_spec(ROOT, t).identity,
                thr_digest=thr_digest(r),
                cluster_id=t,
            )
            for t, r in thrs.items()
        ],
        "configurations": Configurations(A=SYSTEM.identity, B="sha256:" + "9" * 64),
        "repetitions": 1,
        "margin": 0.05,
    }
    fields.update(kw)
    return DecisionProtocol.model_validate(fields)


def test_the_slice_bundle_links_the_whole_chain_and_rescores_offline(
    thrs: dict[str, TaskHealthRecord],
) -> None:
    proto = protocol(thrs)
    files = run_slice(ROOT, proto, list(thrs.values()), SliceRunner())
    report = validate(files)
    assert report.valid, report.problems()
    assert rescore(files).status == "reproduced"

    assert content_identity(DecisionProtocol.model_validate_json(files["protocol.json"])) == (
        proto.identity
    )
    assert SystemSpec.model_validate_json(files["system.json"]).identity == SYSTEM.identity
    for task, record in thrs.items():
        sealed = TaskHealthRecord.model_validate_json(files[f"tasks/{task}/thr.json"])
        assert thr_digest(sealed) == thr_digest(record)

    events = [json.loads(line)["event"] for line in files["journal.jsonl"].splitlines()]
    kinds = [e["kind"] for e in events]
    assert kinds.count("episode_planned") == 4 and kinds.count("episode_scored") == 4
    planned = [e["payload"]["episode"] for e in events if e["kind"] == "episode_planned"]
    assert {p["protocol"] for p in planned} == {proto.identity}
    assert {p["system"] for p in planned} == {SYSTEM.identity}
    outcomes = [e for e in events if e["kind"] == "attempt_outcome"]
    assert all(e["payload"]["provider"]["request_ids"] for e in outcomes)

    verdicts = json.loads(files["verdicts.json"])
    by_episode = {v["episode_id"]: v for v in verdicts}
    episodes = json.loads(files["episodes.json"])
    authz_vulnerable = next(
        e for e in episodes if e["task_id"] == "authz-001" and e["variant"] == "vulnerable"
    )
    graded = by_episode[authz_vulnerable["episode_id"]]
    assert [v["verdict"] for v in graded["verdicts"]] == ["confirmed"]


@pytest.mark.parametrize(
    "change",
    ["system-not-in-protocol", "thr-digest-mismatch", "unknown-task", "unhealthy-thr"],
)
def test_a_run_that_does_not_match_its_protocol_dispatches_nothing(
    thrs: dict[str, TaskHealthRecord], change: str
) -> None:
    proto, records = protocol(thrs), list(thrs.values())
    if change == "system-not-in-protocol":
        proto = protocol(
            thrs, configurations=Configurations(A="sha256:" + "7" * 64, B="sha256:" + "8" * 64)
        )
    elif change == "thr-digest-mismatch":
        records = [records[0]]
    elif change == "unknown-task":
        unknown = proto.cohort[0].model_copy(update={"task_identity": "sha256:" + "6" * 64})
        cohort = [unknown, proto.cohort[1]]
        proto = protocol(thrs, cohort=cohort)
    else:
        data = records[0].model_dump(mode="json")
        data["determinism"]["reproduced"] = False
        data["status"], data["status_reason"] = "unhealthy", "determinism re-run did not reproduce"
        bad = TaskHealthRecord.model_validate(data)
        cohort = [
            proto.cohort[0].model_copy(update={"thr_digest": thr_digest(bad)}),
            proto.cohort[1],
        ]
        proto, records = protocol(thrs, cohort=cohort), [bad, records[1]]
    runner = SliceRunner()
    with pytest.raises(SliceError):
        run_slice(ROOT, proto, records, runner)
    assert runner.seen == []
    with pytest.raises(SliceError):
        plan(ROOT, proto, records, SYSTEM.identity)
