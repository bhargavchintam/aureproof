# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""End-to-end episode orchestration with a fake runner (issue #39); no Inspect needed."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from aureproof.bundle.ledger import LedgerError
from aureproof.contracts import Disposition, EpisodeSpec, LabelSet
from aureproof.oracles.calibration import task_spec
from aureproof.oracles.python_spans import line_counts
from aureproof.runners.orchestrate import run_episode
from aureproof.runners.port import AttemptRequest, AttemptResult, SampleFacts, classify
from aureproof.storage import BlobStore
from aureproof.storage.ledger_store import AttemptLedgerStore

ROOT = Path(__file__).resolve().parents[2]
LABELS = LabelSet.model_validate_json(
    (ROOT / "fixtures/oracles/authz-001/labels.json").read_text("utf-8")
)
VIEW = line_counts(ROOT / "fixtures/security/authz-001/variants/vulnerable")
TOOLS = ["bash", "submit"]
FINDING = json.dumps(
    [
        {
            "cwe": 862,
            "description": "no ownership check",
            "locations": [{"file": "docstore/service.py", "symbol": "delete_document"}],
        }
    ]
).encode()


class FakeRunner:
    def __init__(self, script: list[SampleFacts | Exception]) -> None:
        self.script: Iterator[SampleFacts | Exception] = iter(script)
        self.seen: list[str] = []

    def run_attempt(self, request: AttemptRequest) -> AttemptResult:
        self.seen.append(request.attempt_id)
        step = next(self.script)
        if isinstance(step, Exception):
            raise step
        return classify(step, declared_tools=TOOLS)


def ok(**kw: object) -> SampleFacts:
    base: dict[str, object] = {
        "log_digest": "sha256:" + "b" * 64,
        "model_requests": 2,
        "request_ids": ["req_1", "req_2"],
        "provider_retries": 1,
        "offered_tools": frozenset(TOOLS),
        "runner_run_id": "run-x",
    }
    base.update(kw)
    return SampleFacts(**base)  # type: ignore[arg-type]


@pytest.fixture
def setup(tmp_path: Path) -> tuple[AttemptLedgerStore, BlobStore, AttemptRequest]:
    from aureproof.runners.inspect_runner import InspectRunnerConfig, system_spec

    task = task_spec(ROOT, "authz-001")
    try:
        system = system_spec(
            InspectRunnerConfig(subject="reference", model="mockllm/model", log_dir=tmp_path)
        )
    except Exception:  # inspect not installed: build an equivalent identity by hand
        from aureproof.contracts import SystemSpec

        system = SystemSpec.model_validate(
            json.loads(
                (
                    ROOT / "conformance/contracts/v0.1/system-spec/valid/reference-react.json"
                ).read_text()
            )["instance"]
        )
    episode = EpisodeSpec.plan(
        task=task.identity,
        variant="vulnerable",
        system=system.identity,
        protocol="sha256:" + "3" * 64,
        repetition=0,
    )
    request = AttemptRequest(episode, "", task, system, ROOT, "vulnerable")
    return AttemptLedgerStore(tmp_path / "run"), BlobStore(tmp_path / "cas"), request


def test_confirmed_finding_end_to_end(setup: tuple) -> None:  # type: ignore[type-arg]
    store, blobs, request = setup
    run = run_episode(
        store,
        blobs,
        FakeRunner([ok(capture_status="captured", submission=FINDING)]),
        request,
        LABELS,
        VIEW,
    )
    assert run.score.disposition is Disposition.COMPLETED_WITH_FINDINGS
    assert run.score.credited == ("authz-001-d1",)
    assert blobs.get(run.submission or "") == FINDING  # raw bytes kept by digest
    kinds = [e.kind for e in store.journal.events]
    assert kinds == [
        "episode_planned",
        "attempt_planned",
        "attempt_dispatched",
        "attempt_outcome",
        "episode_finalized",
    ]  # dispatch is durable first
    outcome = store.journal.events[3].payload or {}
    assert outcome["provider"] == {"requests": 2, "retries": 1, "request_ids": ["req_1", "req_2"]}
    assert outcome["log_digest"].startswith("sha256:") and outcome["capture"] == "captured"


def test_infrastructure_failure_is_redispatched_as_a_new_attempt(setup: tuple) -> None:  # type: ignore[type-arg]
    store, blobs, request = setup
    runner = FakeRunner(
        [
            ok(error="httpx.ConnectError: Connection refused", model_requests=0),
            ok(capture_status="captured", submission=FINDING),
        ]
    )
    run = run_episode(store, blobs, runner, request, LABELS, VIEW)
    assert run.attempts == [f"{run.episode_id}/a0", f"{run.episode_id}/a1"]
    records = store.records()
    assert [r.status for r in records] == ["failed", "completed"]  # both kept, never merged
    assert records[0].error_class == "infra:proxy_not_ready"
    assert run.score.disposition is Disposition.COMPLETED_WITH_FINDINGS


def test_agent_errors_are_never_retried(setup: tuple) -> None:  # type: ignore[type-arg]
    store, blobs, request = setup
    run = run_episode(
        store, blobs, FakeRunner([ok(error="AssertionError: agent bug")]), request, LABELS, VIEW
    )
    assert len(run.attempts) == 1 and run.score.disposition is Disposition.AGENT_ERROR


@pytest.mark.parametrize(
    ("facts", "disposition"),
    [
        (
            ok(limit_type="time", capture_status="captured", submission=FINDING),
            Disposition.BUDGET_EXHAUSTED,
        ),
        (ok(stop_reasons=["content_filter"], capture_status="absent"), Disposition.SAFETY_REFUSAL),
        (ok(capture_status="absent"), Disposition.INVALID_OUTPUT),
        (ok(offered_tools=frozenset({"bash", "submit", "web_fetch"})), Disposition.INFRA_FAILURE),
    ],
)
def test_dispositions_come_from_sample_facts(
    setup: tuple,
    facts: SampleFacts,  # type: ignore[type-arg]
    disposition: Disposition,
) -> None:
    store, blobs, request = setup
    assert (
        run_episode(store, blobs, FakeRunner([facts]), request, LABELS, VIEW).score.disposition
        is disposition
    )


def test_redispatch_is_capped_and_runner_exceptions_are_recorded(setup: tuple) -> None:  # type: ignore[type-arg]
    store, blobs, request = setup
    runner = FakeRunner(
        [
            RuntimeError("boom"),
            ok(error="docker daemon not running"),
            ok(error="docker daemon not running"),
        ]
    )
    run = run_episode(store, blobs, runner, request, LABELS, VIEW, max_redispatch=2)
    assert len(run.attempts) == 3 and run.score.disposition is Disposition.INFRA_FAILURE
    first = store.record(run.attempts[0])
    assert (
        first.status == "incomplete" and first.error_class == "infra:runner_exception:RuntimeError"
    )
    assert sum(e.kind == "episode_finalized" for e in store.journal.events) == 1


def test_tool_calls_are_journaled_before_the_outcome(setup: tuple) -> None:  # type: ignore[type-arg]
    """Issue #43: each tool call lands in the journal with its trust tier."""
    from aureproof.runners.port import ToolCall

    store, blobs, request = setup
    calls = [
        ToolCall("bash", "1" * 64, "2" * 64),
        ToolCall("submit", "3" * 64, "4" * 64, error="timeout"),
    ]
    runner = FakeRunner([ok(capture_status="captured", submission=FINDING, tool_calls=calls)])
    run_episode(store, blobs, runner, request, LABELS, VIEW)
    kinds = [e.kind for e in store.journal.events]
    assert kinds.index("tool_observed") > kinds.index("attempt_dispatched")
    assert kinds.count("tool_observed") == 2 and kinds[-2] == "attempt_outcome"
    tools = [e for e in store.journal.events if e.kind == "tool_observed"]
    assert [(e.payload or {})["tool"] for e in tools] == ["bash", "submit"]
    assert {e.observation_source for e in tools} == {"controller_observed"}
    assert (tools[1].payload or {})["error"] == "timeout"


def test_agent_reported_tool_calls_keep_their_lower_trust_tier(setup: tuple) -> None:  # type: ignore[type-arg]
    from aureproof.runners.port import ToolCall

    store, blobs, request = setup
    facts = ok(tool_calls=[ToolCall("Bash", "1" * 64, None)], tool_source="agent_reported")
    run_episode(store, blobs, FakeRunner([facts]), request, LABELS, VIEW)
    [tool] = [e for e in store.journal.events if e.kind == "tool_observed"]
    assert tool.observation_source == "agent_reported"
    assert (tool.payload or {})["output_sha256"] is None


def test_a_duplicate_delivery_publishes_one_result(setup: tuple) -> None:  # type: ignore[type-arg]
    """Issue #55: delivering a finished episode again adds no attempt and no second result."""
    store, blobs, request = setup
    first = run_episode(
        store,
        blobs,
        FakeRunner([ok(capture_status="captured", submission=FINDING)]),
        request,
        LABELS,
        VIEW,
    )
    events = len(store.journal.events)
    runner = FakeRunner([ok(capture_status="captured", submission=b"[]")])
    with pytest.raises(LedgerError):
        run_episode(store, blobs, runner, request, LABELS, VIEW)
    assert runner.seen == []  # nothing was dispatched again
    assert len(store.journal.events) == events
    kinds = [e.kind for e in store.journal.events]
    assert kinds.count("episode_finalized") == 1 and kinds.count("attempt_dispatched") == 1
    assert first.score.credited == ("authz-001-d1",)
