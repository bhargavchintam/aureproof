# Bridge capability coverage

Issue #42 (AP-015). This declares, for the Inspect runner's two subjects, which
capabilities Aureproof **enforces**, which it only **observes**, and the test that
checks each one. Tests under `tests/integration/` run in the Inspect + Docker +
mockllm lane: real sandboxes and the real Claude Code binary, with a scripted
model instead of a provider. The threat-model IDs refer to
[`threat-model.md`](threat-model.md).

## Enforced

| Capability | How | Subject | Test | STRIDE |
| --- | --- | --- | --- | --- |
| No upstream provider key in the sandbox | The bridge serves the model API inside the sandbox; Claude Code gets only the bridge's own `ANTHROPIC_AUTH_TOKEN` and a loopback `ANTHROPIC_BASE_URL` | Claude Code | `test_bridge_qualification.py::test_no_provider_key_or_evaluator_label_reaches_the_sandbox_or_transcript` (a planted host key is absent from the sandbox env and the log) | T-INFO-2 |
| No evaluator labels in the sandbox or transcript | Only the variant's files are mounted | both | the same test (no `labels.json` anywhere in the sandbox; no oracle canary or defect ID in the log); `test_inspect_runner.py::test_reference_tool_calls_are_journaled_and_the_log_is_clean` | T-INFO-1 |
| No network egress | `network_mode: none` | both | `test_bridge_qualification.py::test_sandbox_outbound_traffic_fails` (by address and by name) | T-ELEV-1 |
| Hosted tools withheld | `closed-world`: WebSearch and WebFetch disallowed in Claude Code; the offered tool list must be within the declared one (22 tools observed live, `CLAUDE_CODE_LIVE_ONLY_TOOLS` included) | Claude Code | `test_bridge_qualification.py::test_hosted_tools_are_withheld_and_a_call_to_one_is_rejected` | T-ELEV-2 |
| The Claude Code binary is the pinned one | Each Linux sandbox binary of the pinned version is pinned by sha256 from the release manifest and recorded in the system identity (`settings.binary_sha256`). An unpinned version fails preflight; a cached binary whose hash differs refuses the runner before any dispatch | Claude Code | `tests/runners/test_binary_pins.py` | T-TAMP-4 |
| Unqualified capabilities fail preflight | `preflight()` at runner construction: `web-search`, a non-Anthropic provider for Claude Code, hosted tools for the reference subject, a model that differs from the recorded identity | both | `tests/runners/test_preflight.py` | T-ELEV-3 |
| Token budget | Inspect `token_limit`; exhaustion is `budget_exhausted` in one attempt | both | `test_bridge_qualification.py::test_token_budget_ends_the_episode_without_extra_opportunities`, `test_inspect_runner.py::test_distinct_dispositions_from_the_real_sandbox` | T-DOS-4 |
| Time budget | Inspect `time_limit`; exhaustion is `budget_exhausted` in one attempt | both | `test_bridge_qualification.py::test_time_budget_ends_the_episode_without_extra_opportunities` | T-DOS-4 |
| No hidden retries | `retry_on_error=0`; Claude Code `retry_refusals=0`, `retry_uncaught_errors=0`, `attempts=1`; a sample retried by the runner is a configuration fault | both | `tests/runners/test_classify.py::test_refusal_signal_and_hidden_retries_and_tool_drift` | — |

## Observed and journaled

| Evidence | Trust tier | Test |
| --- | --- | --- |
| Every model call, including Claude Code's streamed calls: count, provider retries, request IDs | `controller_observed` (seen at the bridge, journaled in the attempt outcome) | `test_bridge_qualification.py::test_model_calls_are_journaled_by_the_controller_with_their_trust_tier` |
| Infrastructure re-dispatch | `controller_observed`: each one is its own journaled attempt | `tests/runners/test_orchestrate.py` |
| Reference subject tool calls (input and output digests) | `controller_observed` (Inspect executed them) | `test_inspect_runner.py::test_reference_tool_calls_are_journaled_and_the_log_is_clean` |
| Claude Code tool calls (input digest only) | `agent_reported` (Claude Code executed them itself) | `test_bridge_qualification.py::test_model_calls_are_journaled_by_the_controller_with_their_trust_tier` |

## Disclosed transformations

`system_spec().settings["transformations"]` records what the bridge changes, so it is
part of the system identity. For Claude Code: its Anthropic Messages requests are
served by `sandbox_agent_bridge` and forwarded to the Inspect model API, and
WebSearch and WebFetch are disallowed. The reference subject applies none.

## Not covered

- **Action and request budgets.** ADR-0007 declares tokens, time and one attempt.
  There is no action or request budget to enforce. Adding one to the protocol needs
  a runner limit and a test first; until then preflight has nothing to accept.
- **Streaming chunks.** Model calls are recorded whole, as the bridge saw them;
  individual stream chunks are not journaled.
- **A real provider key.** The planted-key test proves isolation of whatever the host
  holds. The digest check against a real key runs when a key exists (#7).
- **The qualified host.** These tests ran on Docker Desktop and GitHub's Linux
  runners. The dedicated Linux host (#32) must pass the same lane before release
  claims.
- **`web-search`.** Not implemented; it fails preflight.
