# Spike: Inspect AI as the v0.1 runner (Day 2, issue #7, AP-034)

- Date: 2026-10-11
- Fixture: `authz-001` (both variants), cluster `authz-001`
- Host: macOS 27 on Apple Silicon (arm64), Docker Desktop engine 29.8.1
- Pins: `inspect-ai==0.3.278`, `inspect-swe==0.2.71`, `anthropic` 1.13 (extra `inspect`),
  Claude Code 2.1.287 (`linux-arm64`, host-cached and checksum-verified by inspect_swe),
  sandbox image `python:3.12-slim@sha256:a6e34c59…dc11b1`
- Code: [`spikes/inspect_day2/`](../../spikes/inspect_day2/); regression test:
  [`tests/integration/test_inspect_spike.py`](../../tests/integration/test_inspect_spike.py)

## Verdict

**Inspect passes as the v0.1 runner.** Checks 1, 3, 4 and 5 pass with evidence.
Check 2 passes for the reference subject and for Claude Code's plumbing (it runs offline through the bridge and is graded as `no_submission` when it writes nothing).
The **live** Claude Code episode on a real model is still open. It needs a provider key, and
[`live.py`](../../spikes/inspect_day2/live.py) runs it in one command. ADR-0002 and ADR-0003 are accepted.
The plain-Docker fallback is not needed.

## Checks

| # | Check (plan v2 §3.3) | Result | Evidence |
| --- | --- | --- | --- |
| 1 | The bridge works with the sandbox at `network_mode: none` | **Pass** | The `bridge_probe` subject runs a script in the sandbox. It posts to `http://localhost:13131/v1/messages` and gets the model's reply, and the call appears in the log as a controller-side `ModelEvent`. A TCP connection to `1.1.1.1:443` fails with `Network is unreachable`. The sandbox env holds only the image's own variables (`GPG_KEY`, `HOME`, `HOSTNAME`, `LANG`, `PATH`, `PYTHON_*`). In the `live.py --dry-run` rehearsal, a canary key set in the controller hashes to no sandbox env value and appears in no log member. |
| 2 | Reference subject and Claude Code write `findings.json` as a declared artifact | **Pass (reference); plumbing pass (Claude Code); live pending** | The scripted subject (`react()` + `bash()` on `mockllm`) writes `findings.json`, which is collected and graded. Claude Code 2.1.287 starts in the no-network sandbox, its model traffic goes through the bridge (about 15k tokens per sample), and its missing file is recorded as `no_submission`. The live run on Haiku 4.5 still needs a key. |
| 3 | The label matcher runs in the controller and never reads agent-writable verdict files | **Pass** | The scripted agent plants `verdict.json` (`"confirmed"`) and `reward.txt` (`1`) next to its finding. The vulnerable variant scores `confirmed` and the repaired variant scores `refuted`, so the forgeries had no effect. The scorer reads only the bytes captured from `findings.json`. |
| 4 | Inspect and `inspect_swe` pin cleanly with uv, and the Python floor is confirmed | **Pass** | Optional extra `inspect` with exact pins. `uv lock --check` is clean, the stack runs on 3.12.14, and it resolves for 3.13 (resolve only, not executed). Both packages need Python ≥3.10, so the project floor stays 3.12. The core install (`uv sync --frozen`, as in CI) does not pull Inspect in. |
| 5 | The runner does single attempts, and Aureproof records retries | **Pass, with conditions** | With `retry_on_error=0`, a failed first attempt stays an errored, unscored sample, which maps to `infra_failure`. With `retry_on_error=1`, the failure survives only as an `error_retries` stub (message and traceback, 0 events), and the successful retry replaces the sample. That is lossy, so Aureproof should own re-dispatch (ADR-0003). Provider-level retries show up per call in `ModelEvent.retries` and `request_ids`. |

## Findings that change the design

1. **Collect, then match (constrains AP-012 and the Bundle spec).**
   - Re-scoring a saved log has **no sandbox**, so a scorer that reads `findings.json` from the container cannot be re-run.
   - The spike splits the work in two:
     - `collect_findings` is a solver step that runs after the agent. It reads the file once and stores the raw text and its sha256 in the sample store, which is logged.
     - `findings_matcher` is a pure scorer over those captured bytes.
   - Live scoring and `score(log, …)` then run the same code and give identical verdicts.
   - The captured bytes and digest are the submission evidence the bundle seals.
2. **`claude_code` defaults need overriding.** Each of these changes the measurement, so the defaults are unsafe for us:
   - `web_search` is **on** unless `disallowed_tools` names `WebSearch`.
   - `retry_refusals=3` would retry refusals away, which breaks the `safety_refusal` invariant.
   - `retry_uncaught_errors=3` creates hidden attempts.
   - `attempts>1` scores mid-run and continues, which is a hidden continuation.

   The spike pins `disallowed_tools=["WebSearch", "WebFetch"]`, `retry_refusals=0`, `retry_uncaught_errors=0`, and leaves `attempts=1`. The runner adapter must set these and record them in the `SystemSpec`.
3. **Claude Code's tool surface is wide.** Even with web tools disallowed, it offers 18 tools, including `Agent`, `Workflow`, `Cron*`, `EnterWorktree` and `SendMessage`. This is part of the system identity.
   - Record the offered tool list per episode. It is available from the `ModelEvent`s.
   - Decide an allowlist for the controlled-interface mode (plan §3.6).
4. **Log status is not episode status.** With `fail_on_error=False`, a log whose samples all errored still reports `status: success`. Aureproof must derive dispositions per sample, from `sample.error`, the capture status and the score, never from the log header.
5. **Bridge endpoints need controller-side SDKs.** The Anthropic Messages route needs `anthropic`; the OpenAI-compatible route needs `openai`. The spike's first probe on `/v1/chat/completions` got an HTTP 400 for exactly this reason. Pin only the SDK for the protocol you use.
6. **Agent binaries are host-side and pinned.** inspect_swe downloads Claude Code on the **host**, verifies its checksum, caches it, and writes it into the container. With an exact version (never `stable`/`latest`), the sandbox needs no network at any point. Pre-cache the sandbox's platform (`linux-arm64` on Apple Silicon).
7. **Fast release cadence.** inspect-ai 0.3.278 shipped two days before this spike. Pin exact versions and keep `test_inspect_spike.py` as the contract test that upgrades must pass.
8. **macOS is fine for this spike, not for qualification.** Docker Desktop enforced `network_mode: none` here. Isolation *qualification* (plan §7) still happens on the Linux host (`scripts/check_host.sh`).

## Reproduce

```bash
uv sync --extra inspect
uv run --extra inspect pytest tests/integration/test_inspect_spike.py   # scripted + probe, no key
uv run --extra inspect python spikes/inspect_day2/live.py --dry-run     # full rehearsal, no key
uv run --extra inspect python spikes/inspect_day2/live.py               # live; needs ~/.aureproof-spike.env
```

Logs and run summaries go to `spikes/inspect_day2/logs/`, which git ignores. Run summaries record each log's sha256.

## Open items

- **Live Claude Code episode** (completes check 2). This needs `ANTHROPIC_API_KEY` in `~/.aureproof-spike.env` (mode 600). Paste the resulting `live-summary-*.json` into #7.
- ~~The spike test was flaky.~~ **Fixed.** The failure reproduced in 1 of 12 runs with captured output: `URLError(ConnectionRefusedError)` from the bridge probe. The probe connected before the bridge's in-container proxy was listening. It now waits up to 30 s for the port before calling the proxy. **AP-012 must do the same**: never assume the proxy is ready when `sandbox_agent_bridge()` yields.
- The spike matcher is a stand-in. The real rules M1–M9 come with AP-005 and AP-007.
