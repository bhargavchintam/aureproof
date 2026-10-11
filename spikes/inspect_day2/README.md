<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Day-2 Inspect spike (issue #7, AP-034)

Disposable spike code that answers the five runner checks in plan v2 §3.3. The
results and design findings are in
[`docs/research/spike-inspect-day2.md`](../../docs/research/spike-inspect-day2.md).
The production adapter is AP-012 (`src/aureproof/runners/`). Don't import this
code from `src/`.

| File | Purpose |
| --- | --- |
| `task.py` | Inspect task over both `authz-001` variants. `-T subject=scripted\|bridge_probe\|claude_code` |
| `agents.py` | Scripted `mockllm` policy (plants forged verdict files), bridge probe, failure injection |
| `scorer.py` | `collect_findings` (sandbox → logged store) and `findings_matcher` (pure, stand-in for AP-007) |
| `rescore.py` | Offline re-score of a saved log; must equal the live verdicts |
| `live.py` | One-command live Claude Code run with key-isolation and leak checks (`--dry-run` needs no key) |
| `compose.yaml` | Digest-pinned sandbox with `network_mode: none` |

```bash
uv sync --extra inspect
uv run --extra inspect inspect eval spikes/inspect_day2/task.py -T subject=scripted \
    --model mockllm/model --log-dir spikes/inspect_day2/logs --retry-on-error 0
uv run --extra inspect python spikes/inspect_day2/live.py --dry-run
```

**Live run:** put `ANTHROPIC_API_KEY=...` in `~/.aureproof-spike.env` and
`chmod 600` it. Then run `live.py` with no flags. The default model is Haiku 4.5,
with a budget of 400k tokens and 900 s per sample. The key is read into the
controller process only. The script fails if any sandbox env value hashes to the
key or if the key appears in any log. Logs and summaries go to `logs/`, which git
ignores.
