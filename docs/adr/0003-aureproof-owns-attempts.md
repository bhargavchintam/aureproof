<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# ADR-0003: Aureproof owns attempt identity and retries

- Status: accepted (2026-10-11, Day-2 spike, issue #7)
- Date: 2026-10-07
- Deciders: lead maintainer

## Context

A core invariant is that attempts never silently become extra successful
trials. Harbor's retry logic deletes the failed attempt's directory, which
would erase exactly the record the invariant depends on. More generally, a
runner optimized for throughput is the wrong owner of experimental accounting.

## Decision

The runner executes a **single attempt** per dispatch (`max_retries = 0` or the
adapter's equivalent). Aureproof assigns attempt IDs, schedules repetitions, and
records every attempt — including transport retries and infrastructure failures
— in its own journal. Retry classification (agent self-repair vs. infrastructure
retry vs. hidden continuation) is made and stored by Aureproof.

## Consequences

- Easier: a faithful, auditable attempt record independent of the runner.
- Harder: Aureproof must implement scheduling and restart recovery (plan §3.4).
- Revisit: if a future runner offers attempt accounting that meets the invariant verifiably.

## Spike evidence (2026-10-11, Inspect 0.3.278)

Full notes: [`docs/research/spike-inspect-day2.md`](../research/spike-inspect-day2.md).

- **Inspect's own retries lose evidence.** With `retry_on_error=1`, the failed attempt survives only as an `EvalSample.error_retries` stub (message and traceback, and only the events back to the last model call), and the successful retry replaces the sample. That violates the invariant, so it is not used.
- **The adapter's single-attempt settings:**
  - `retry_on_error=0` and `fail_on_error=False`. A failed attempt then stays an errored, unscored sample, which Aureproof records as `infra_failure` and re-dispatches under a new attempt ID.
  - For `inspect_swe` agents: `retry_uncaught_errors=0`, `retry_refusals=0` (a refusal is `safety_refusal`, never retried away), and `attempts=1` (no hidden continuation).
- **Provider-level retries** are visible per call as `ModelEvent.retries` and `request_ids`. Aureproof records them as infrastructure attempts (plan §3.6).
- **The log header is not an episode outcome.** With `fail_on_error=False`, a log whose samples all errored still reports `status: success`. Dispositions are derived per sample.
