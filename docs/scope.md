<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Scope (v0.1)

Condensed from [`aureproof-plan-v2.md`](aureproof-plan-v2.md) §1. **Frozen on
2026-10-27** (issue #5, AP-001). Changing it needs a new ADR and a reviewed
amendment.

- Primary metric: **strict confirmed yield** ([ADR-0006](adr/0006-primary-metric-strict-confirmed-yield.md)).
- External subject: **Claude Code over Anthropic Messages**, native-capability mode,
  in the `closed-world` configuration by default, with `web-search` as a declared
  variant. Budget: 400k tokens, 15 min, one attempt
  ([ADR-0007](adr/0007-external-agent-and-interface.md)).

## The promise

> Given a versioned security task with a healthy, frozen task-health record, an
> identified agent system, and a signed pre-registered protocol, Aureproof
> produces a signed result bundle. Another engineer can verify its verdicts,
> denominators, failures, refusals, and evidence; re-score it offline; and
> dispute it through a recorded adjudication path.

## Personas

| Persona | Job to be done | v0.1 feature |
| --- | --- | --- |
| Eval engineer (lab / AISI / platform team) | "Is this regression real, and can I defend the call?" | Decision gate + GitHub Action; signed bundle |
| Security-agent builder | "What's my false-alarm rate on code I control?" | Precision-first fixtures; anti-spray control; per-category outcomes |
| Benchmark maintainer | "Which of my tasks are broken?" | Task-health records + `aureproof task validate` |

## Goals

- Three open specs (task health, evidence bundle, decision protocol) with a reference implementation.
- A ~20-case precision-first synthetic Python fixture pack with health records.
- An Inspect runner adapter; one reference and one external subject; static + direct-model baselines.
- A signed, offline-re-scorable evidence bundle.
- An exact paired decision gate (CLI + GitHub Action).
- An offline tutorial that needs no credentials, and an independent reproduction.

## Non-goals (v0.1)

- Executing agent-submitted PoC code (v0.2), real-CVE tasks, patch grading.
- Chat / RAG / voice / multi-agent systems; broad language coverage; training.
- A hosted dashboard, Kubernetes, multiple storage backends, a custom scheduler, a universal leaderboard.

## Primary intent

A credible, reproducible, standards-aligned open-source project whose
reputation rests on corrected verdicts, honest comparisons, and independent
reproduction rather than on breadth of features. Synthetic fixtures measure **controlled skills,
not real-world capability**, and the project says so wherever it reports.
