<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# ADR-0002: Inspect AI as the first runner; Harbor in v0.2

- Status: accepted (2026-10-11, Day-2 spike, issue #7)
- Date: 2026-10-07
- Deciders: lead maintainer

## Context

The original plan pinned Harbor as the sole runner. Verification of Harbor
v0.24.0 found behavior that conflicts with the evidence invariants: the default
verifier lets the agent write the reward file (#2551), a PoC executed by the
separate verifier can still write it (#1779), retries delete the failed
attempt, real provider keys are forwarded into the sandbox (no built-in proxy,
#159), and usage telemetry is on by default. Inspect AI's
`sandbox_agent_bridge()` proxies the agent's model calls, withholds hosted tools
unless granted, runs scorers in the controller, and re-scores saved logs.

## Decision

Use Inspect AI as the v0.1 runner, behind a thin `Runner` port, with a
plain-Docker fallback. Reintroduce Harbor in v0.2 for separate-verifier PoC
execution, configured with `environment_mode = "separate"`, `max_retries = 0`,
`HARBOR_TELEMETRY = off`, and in-process verdict computation.

## Consequences

- Easier: key isolation and hosted-tool withholding come from the bridge; much of the inference-gateway work shrinks.
- Harder: a second runner adapter (Harbor) later; both must satisfy the same contract.
- Harder: Inspect releases often (0.3.278 at acceptance); pin exact versions and keep `tests/integration/test_inspect_spike.py` as the upgrade contract test.
- Revisit: if the live Claude Code episode (issue #7) cannot produce a submission through the bridge, or a pinned upgrade breaks the contract test.

## Production adapter (2026-10-28, issue #39)

`aureproof.runners.inspect_runner` behind the `Runner` port (`aureproof.runners.port`).
- One Inspect sample per attempt, with `retry_on_error=0` and `fail_on_error=False`.
- Captured `findings.json` bytes and their SHA-256 go into the logged store and the content-addressed store.
- Outcomes are classified per sample, and only infrastructure failures are re-dispatched, as new attempts (`aureproof.runners.orchestrate`).
- **Known gap:** the bridge doesn't wait for its in-sandbox proxy to be ready. A connection failure before any model call is classified `infra:proxy_not_ready` and re-dispatched visibly. Candidate upstream fix: M5.

## Spike evidence (2026-10-11)

Full notes: [`docs/research/spike-inspect-day2.md`](../research/spike-inspect-day2.md).
Pins: `inspect-ai==0.3.278`, `inspect-swe==0.2.71`, Claude Code 2.1.287.

- The bridge works with the sandbox at `network_mode: none`. The proxy listens on the container's loopback and relays over the exec channel. Egress is blocked, no provider variable is in the sandbox env, and a canary key reaches neither the sandbox nor any log.
- The scorer runs in the controller and ignores planted `verdict.json` and `reward.txt` files. Grading is collect-then-match, so re-scoring a saved log reproduces the live verdicts with no sandbox.
- The stack pins cleanly with uv (optional extra `inspect`). Python floor: Inspect needs ≥3.10, and the project stays at ≥3.12.
- Required `inspect_swe.claude_code` settings: `disallowed_tools=["WebSearch", "WebFetch"]` (web search is otherwise on), `retry_refusals=0`, `retry_uncaught_errors=0`, `attempts=1`, and an exact, host-cached `version`.
- Still open: a live Claude Code episode on a real model (`spikes/inspect_day2/live.py`).
