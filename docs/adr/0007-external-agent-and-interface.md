<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# ADR-0007: External agent, model protocol, interface modes, hosted tools and budgets

- Status: accepted
- Date: 2026-10-27
- Deciders: lead maintainer (issue #5, AP-001). Each choice below was made
  explicitly; none is inferred from implemented defaults.

## Context

ADR-0002 made Inspect AI the v0.1 runner. The plan needs one external agent (a
real product) and one reference subject, an inference protocol through the
bridge, and an explicit policy for interface mode, provider-hosted tools and
per-episode budgets. The Day-2 spike showed that `inspect_swe.claude_code` runs
offline through the bridge and that some of its defaults are unsafe for
measurement (web search on, refusal and crash retries).

## Decision

**Subjects and protocol**

| Role | Subject | Protocol |
| --- | --- | --- |
| External subject | **Claude Code** via `inspect_swe.claude_code`, exact pinned version, host-cached binary (never `stable`/`latest`) | **Anthropic Messages**, through `sandbox_agent_bridge()` |
| Reference subject | Inspect ReAct agent (or mini-swe-agent, decided in AP-016) | The eval model through Inspect |

The model for each configuration is fixed by the signed Decision Protocol, not here.

**Interface modes** (plan §3.6). Never compare across modes.

- Claude Code runs in **native-capability** mode: its own built-in tools. The
  offered tool list is recorded per episode in the `SystemSpec`.
- The reference subject runs in **controlled-interface** mode: `bash()` in the
  sandbox only. It is Inspect's `react()` with a pinned system prompt
  (`aureproof.runners.reference`; its digest is `SystemSpec.prompts["system"]`, so
  any edit is a new system), `attempts=1` and `retry_refusals=0`. The prompt
  carries no labels, scoring rules or feedback.

**Tool calls** are journaled per attempt as `tool_observed` events, by digest
(inputs and outputs stay in the runner log). The reference subject's calls are
executed by the harness, so they are `controller_observed`. Claude Code runs its
own tools, so its calls, read from its model responses, are `agent_reported`,
with no observed output. Only `tool_observed` may carry the lower trust tier;
every lifecycle event stays controller-observed.

**Hosted tools.** Two declared configurations, each its own system identity;
results are never pooled across them.

| Configuration | Hosted tools | Use |
| --- | --- | --- |
| `closed-world` (**default and primary**) | None: web search, web fetch, code execution and remote MCP withheld at the bridge; Claude Code gets `disallowed_tools=["WebSearch", "WebFetch"]` | All gate decisions and headline results |
| `web-search` | Provider web search only (bridge `web_search=True`); fetch, code execution and MCP still withheld | A declared, secondary variant, reported separately and flagged for contamination risk: search can surface fixture-adjacent material |

Any request for a withheld tool is recorded as an event.

**Budgets** (per episode; the signed protocol may tighten, never silently loosen):
400,000 tokens, 15 minutes wall-clock, **one attempt**. Hitting a limit gives
`budget_exhausted`, which is graded (scoring spec Q4). Only Aureproof re-dispatches,
and only after an infrastructure failure (ADR-0003).

**Required `claude_code` settings:** `retry_refusals=0` (a refusal is
`safety_refusal`, never retried away; plan §7.4), `retry_uncaught_errors=0`,
`attempts=1`, an exact `version`, and the hosted-tool settings above.

## Consequences

- Easier: one real-product subject with a proven offline path; explicit, recorded
  system identities; a closed world by default.
- Harder: live runs need an Anthropic key (#7, #48), and the `web-search`
  configuration doubles the runs for any claim that uses it.
- Revisit: if the external subject changes (e.g. Codex CLI), write a new ADR. The
  protocol, tool surface and defaults differ per agent.

## Update 2026-10-28: bridge qualification (#42)

`preflight()` now rejects any configuration the bridge cannot qualify, when the
runner is built and before any dispatch. `web-search` is one of them: the runner
never enables the bridge's `web_search`, and hosted search needs a live run to
qualify (#7). Until then only `closed-world` runs. The Claude Code protocol
translation is recorded in `SystemSpec.settings["transformations"]`. Coverage, and
what stays uncovered, is declared in `docs/bridge-coverage.md`.
