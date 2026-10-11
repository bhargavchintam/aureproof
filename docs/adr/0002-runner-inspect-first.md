<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# ADR-0002: Inspect AI as the first runner; Harbor in v0.2

- Status: proposed (confirm with the M0 Day-2 spike)
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
- Revisit: after the Day-2 spike (bridge under `network_mode: none`, `findings.json` artifact, in-controller scorer, uv-pinnable). Record the result here.
