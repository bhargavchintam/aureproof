# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""The Runner port and the classification of one attempt (issue #39).

No runner library is imported here, so these rules are tested in ordinary CI.
A runner executes **one** attempt (ADR-0003) and reports plain facts; this
module turns them into an attempt outcome and the controller-observed
episode signals. Per-sample facts decide, never a log header.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from aureproof.contracts import EpisodeSignals, EpisodeSpec, RunnerOutcome, SystemSpec, TaskSpec

Outcome = Literal["response", "terminal_error", "unknown"]
LIMIT_TYPES = frozenset({"token", "time", "working", "message", "turn", "cost", "context"})
# Errors that are the environment's fault, not the agent's: re-dispatchable.
_INFRA = re.compile(
    r"(?i)(connection refused|econnrefused|connecterror|proxy|sandbox|docker|compose"
    r"|timed? ?out|rate.?limit|overloaded|service unavailable|\b5\d\d\b|apiconnectionerror)"
)
_PROXY = re.compile(r"(?i)(connection refused|econnrefused|connecterror|proxy)")


@dataclass(frozen=True)
class AttemptRequest:
    episode: EpisodeSpec
    attempt_id: str
    task: TaskSpec
    system: SystemSpec
    root: Path  # repository root that TaskSpec paths are relative to
    variant: str


@dataclass(frozen=True)
class SampleFacts:
    """What the runner observed for the single sample of one attempt."""

    error: str | None = None
    limit_type: str | None = None
    capture_status: Literal["captured", "absent", "missing"] = "missing"
    submission: bytes | None = None
    stop_reasons: Sequence[str] = ()
    model_requests: int = 0
    provider_retries: int = 0
    request_ids: Sequence[str] = ()
    offered_tools: frozenset[str] = frozenset()
    hidden_retries: int = 0  # runner-level sample retries; must be 0 (ADR-0003)
    log_path: Path | None = None
    log_digest: str | None = None
    runner_run_id: str | None = None


@dataclass(frozen=True)
class AttemptResult:
    outcome: Outcome
    signals: EpisodeSignals
    submission: bytes | None
    capture: Literal["captured", "absent"] | None
    error_class: str | None
    log_digest: str | None
    runner_run_id: str | None
    provider: dict[str, object] = field(default_factory=dict)
    offered_tools: frozenset[str] = frozenset()


class Runner(Protocol):
    def run_attempt(self, request: AttemptRequest) -> AttemptResult: ...


def classify(facts: SampleFacts, *, declared_tools: Sequence[str]) -> AttemptResult:
    """Outcome and signals for one attempt, from per-sample facts only."""
    provider = {
        "requests": facts.model_requests,
        "retries": facts.provider_retries,
        "request_ids": list(facts.request_ids),
    }
    refusal = "content_filter" in facts.stop_reasons  # D3 applies only with no findings
    evidence = facts.log_digest is not None

    def result(outcome: Outcome, runner: RunnerOutcome, error_class: str | None) -> AttemptResult:
        captured = facts.capture_status == "captured"
        return AttemptResult(
            outcome=outcome,
            signals=EpisodeSignals(
                evidence_complete=evidence, runner_outcome=runner, refusal_signal=refusal
            ),
            submission=facts.submission if captured else None,
            capture=None if facts.capture_status == "missing" else facts.capture_status,
            error_class=error_class,
            log_digest=facts.log_digest,
            runner_run_id=facts.runner_run_id,
            provider=provider,
            offered_tools=facts.offered_tools,
        )

    if facts.hidden_retries:
        # A runner retried the sample itself: the evidence of attempts is incomplete.
        return result("terminal_error", RunnerOutcome.INFRA_ERROR, "config:runner_retried_sample")
    undeclared = sorted(facts.offered_tools - set(declared_tools))
    if undeclared:
        return result(
            "terminal_error",
            RunnerOutcome.INFRA_ERROR,
            "config:tool_surface_mismatch:" + ",".join(undeclared),
        )
    if facts.error is not None:
        if _PROXY.search(facts.error) and facts.model_requests == 0:
            return result("terminal_error", RunnerOutcome.INFRA_ERROR, "infra:proxy_not_ready")
        if _INFRA.search(facts.error):
            return result("terminal_error", RunnerOutcome.INFRA_ERROR, "infra:runner_error")
        return result("terminal_error", RunnerOutcome.AGENT_ERROR, "agent:error")
    if facts.limit_type is not None:
        if facts.limit_type in LIMIT_TYPES:
            return result("response", RunnerOutcome.LIMIT_EXCEEDED, f"limit:{facts.limit_type}")
        return result(
            "terminal_error", RunnerOutcome.INFRA_ERROR, f"infra:limit:{facts.limit_type}"
        )
    if not evidence:
        return result("unknown", RunnerOutcome.INFRA_ERROR, "infra:no_log")
    return result("response", RunnerOutcome.OK, None)


def redispatchable(result: AttemptResult) -> bool:
    """Only infrastructure failures earn a new attempt; agent errors never do."""
    return result.outcome != "response" and (result.error_class or "").startswith("infra:")
