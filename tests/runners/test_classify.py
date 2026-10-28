# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Per-sample classification of one attempt (issue #39); no Inspect needed."""

from __future__ import annotations

import pytest

from aureproof.contracts import RunnerOutcome
from aureproof.runners.port import SampleFacts, classify, redispatchable

TOOLS = ["bash", "submit"]
DIGEST = "sha256:" + "a" * 64


def facts(**kw: object) -> SampleFacts:
    base: dict[str, object] = {
        "log_digest": DIGEST,
        "model_requests": 2,
        "offered_tools": frozenset({"bash", "submit"}),
    }
    base.update(kw)
    return SampleFacts(**base)  # type: ignore[arg-type]


def test_clean_attempt_with_captured_submission() -> None:
    r = classify(facts(capture_status="captured", submission=b"[]"), declared_tools=TOOLS)
    assert (r.outcome, r.signals.runner_outcome, r.capture, r.submission) == (
        "response",
        RunnerOutcome.OK,
        "captured",
        b"[]",
    )
    assert r.signals.evidence_complete and not redispatchable(r)


@pytest.mark.parametrize(
    ("error", "requests", "error_class", "runner_outcome", "retry"),
    [
        (
            "httpx.ConnectError: Connection refused",
            0,
            "infra:proxy_not_ready",
            RunnerOutcome.INFRA_ERROR,
            True,
        ),
        ("docker compose up failed", 2, "infra:runner_error", RunnerOutcome.INFRA_ERROR, True),
        (
            "anthropic.RateLimitError: 429 rate_limit_error",
            3,
            "infra:runner_error",
            RunnerOutcome.INFRA_ERROR,
            True,
        ),
        ("ZeroDivisionError: division by zero", 3, "agent:error", RunnerOutcome.AGENT_ERROR, False),
    ],
)
def test_errors_split_into_infrastructure_and_agent(
    error: str, requests: int, error_class: str, runner_outcome: RunnerOutcome, retry: bool
) -> None:
    r = classify(facts(error=error, model_requests=requests), declared_tools=TOOLS)
    assert (r.error_class, r.signals.runner_outcome, redispatchable(r)) == (
        error_class,
        runner_outcome,
        retry,
    )


def test_limits_are_graded_responses_not_retries() -> None:
    r = classify(facts(limit_type="token", capture_status="absent"), declared_tools=TOOLS)
    assert r.outcome == "response" and r.signals.runner_outcome is RunnerOutcome.LIMIT_EXCEEDED
    assert not redispatchable(r)


def test_refusal_signal_and_hidden_retries_and_tool_drift() -> None:
    assert classify(
        facts(stop_reasons=["content_filter", "tool_calls"]), declared_tools=TOOLS
    ).signals.refusal_signal
    hidden = classify(facts(hidden_retries=1), declared_tools=TOOLS)
    assert hidden.error_class == "config:runner_retried_sample" and not redispatchable(hidden)
    drift = classify(
        facts(offered_tools=frozenset({"bash", "submit", "web_search"})), declared_tools=TOOLS
    )
    assert drift.error_class == "config:tool_surface_mismatch:web_search"
    assert not redispatchable(drift)  # a configuration fault does not go away by retrying


def test_missing_log_is_unknown_and_evidence_incomplete() -> None:
    r = classify(facts(log_digest=None), declared_tools=TOOLS)
    assert r.outcome == "unknown" and not r.signals.evidence_complete and redispatchable(r)
