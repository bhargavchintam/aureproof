# M2 live slice

Issue #47. The run log of the M2 live slice ([procedure](../guides/live-slice.md)):
one budgeted, pre-registered run of configuration A on the three calibrated pairs,
sealed, signed and re-scored offline. Host for every attempt: macOS 27.2 (arm64),
Docker Desktop 29.8.2, which counts as development evidence, not the qualified
Linux host (#32), because the key is not on that host.

## Attempt 1 (2026-10-29): stopped by the runner's own checks

Protocol [`protocols/m2-slice/`](../../protocols/m2-slice/), identity
`sha256:244fc6d8…5cea2e`, signed by `sign.yml` on main before the run.

The first try crashed at the first episode outcome. Inspect 0.3.283 reports provider
request IDs as `ModelRequestId(id, header, status)` objects, and the ledger takes
strings (`LedgerError: attempt_outcome: invalid payload (5 errors)`). The mock and
scripted models of the Docker lane report no request IDs, so no test had reached this.
The runner now records each ID's string (`tests/runners/test_inspect_facts.py`).

The rerun completed and sealed [`bundles/m2-slice-attempt-1/`](../../bundles/m2-slice-attempt-1/):
valid, and the offline re-score is `reproduced`. But all six episodes are
`infra_failure` with
`error_class: config:tool_surface_mismatch:TaskCreate,TaskGet,TaskList,TaskUpdate`.
With a real model, Claude Code 2.1.287 offers its four in-session task-list tools on
top of the 18 declared tools, which were taken from the scripted model of the
Day-2 spike. The runner refuses to grade an episode whose tool surface differs from
the declared one, and it does not retry a configuration fault. That is the intended
fail-closed behavior, so no result was graded or seen. Claude Code had run, though:
51 tool calls were observed and a submission was captured in each episode.

| Count | Value |
| --- | --- |
| Episodes | 6 (3 tasks x 2 variants), one attempt each |
| Provider requests | 4–5 per episode, no provider retries |
| `infrastructure_failure_rate` | 6/6 |
| `evidence_incomplete_rate` | 0/6 (sealed `complete`) |

The four tools are local to the session and use no network, so they are now
declared (`CLAUDE_CODE_LIVE_ONLY_TOOLS`), and a test pins the declared surface to the
22 tools observed live. That changes both system identities, so the protocol was
revised, not edited: [`protocols/m2-slice-2/`](../../protocols/m2-slice-2/), signed before
attempt 2. Only the configurations and the name changed.

## Attempt 2 (2026-10-29): the chain, end to end

Protocol [`protocols/m2-slice-2/`](../../protocols/m2-slice-2/), identity
`sha256:368664cb…e7c382`, signed by `sign.yml` on main (run 40855217877) before the
run. Configuration A: Claude Code 2.1.287 via Inspect 0.3.283 and inspect_swe 0.2.72,
`anthropic/claude-haiku-4-5-20251001`, sandbox `python@sha256:a6e34c59…edc11b1` with
`network_mode: none`, 400k tokens and 900 s per episode, one attempt.

```text
$ uv run --extra inspect aureproof run --protocol protocols/m2-slice-2/protocol.json \
    --thr protocols/m2-slice/thr-authz-001.json --thr protocols/m2-slice/thr-path-001.json \
    --thr protocols/m2-slice/thr-authz-002.json --subject claude_code \
    --model anthropic/claude-haiku-4-5-20251001 --out bundles/m2-slice-2
wrote bundles/m2-slice-2: valid=True offline re-score: reproduced
```

[`bundles/m2-slice-2/`](../../bundles/m2-slice-2/) is sealed `complete`, with 86 journal
events: planning, dispatch, 4–6 controller-observed model calls per episode (each with
its provider request ID), tool observations, the captured submission and the
controller's verdicts.

| Task | Variant | Disposition | Verdicts |
| --- | --- | --- | --- |
| `authz-001` | vulnerable | completed_with_findings | `confirmed` (d1), `unresolved:class_mismatch` |
| `authz-001` | repaired | completed_with_findings | `refuted`, `refuted` |
| `path-001` | vulnerable | completed_with_findings | `confirmed` (d1), `refuted` |
| `path-001` | repaired | completed_with_findings | `refuted`, `refuted` |
| `authz-002` | vulnerable | completed_with_findings | `confirmed` (d1), `refuted`, `refuted` |
| `authz-002` | repaired | completed_with_findings | `refuted` |

| Metric | Value |
| --- | --- |
| Known-defect recall | 3/3 |
| Strict confirmed yield (primary) | 3/12 |
| Scoped false-alarm rate | 8/39 |
| Unresolved fraction | 1/12 |
| Operational completion | 6/6 |
| Infrastructure failure, refusal, evidence-incomplete | 0/6 each |

**Reading.** Claude Code on Haiku 4.5 found every labeled defect. It also reported a
false claim on every repaired variant, and three of every four findings were not
the labeled defect. That is the precision gap the primary metric is built to show,
and what a recall-only benchmark would miss. This is one run of one configuration on
three synthetic pairs: it shows that the evidence chain works, and it is not a
capability estimate. With three clusters a comparison could not reach pass or fail
anyway.

**Limits.** macOS development host, not the Linux runner. The THRs are self-reviewed
and unfrozen (ADR-0005 amendment). The one unresolved finding stays unresolved until
adjudicated. The bundle is signed by `sign.yml` in a follow-up, and a third party's
offline verification is still to be recorded.
