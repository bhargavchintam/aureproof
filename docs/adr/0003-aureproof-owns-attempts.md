<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# ADR-0003: Aureproof owns attempt identity and retries

- Status: proposed (paired with ADR-0002)
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
