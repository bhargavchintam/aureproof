<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Maintainer actions

Everything that still needs a person, as of 2026-10-28. Each item is one action
by the maintainer. Once it's done, the follow-up work in the right-hand column
can be done in the repository. The M2 stop/go (#47) needs all of them.

| # | Action (maintainer) | Unblocks |
| --- | --- | --- |
| [#31](https://github.com/bhargavchintam/aureproof/issues/31) | **Name the independent reviewer.** Ask one person who can read Python and security labels. Add them to `MAINTAINERS.md` and `CODEOWNERS`, and agree a cadence (for example, one review pass per milestone gate). The [reviewer packet](#reviewer-packet) is what they check. | Accepting #9, then #12, #14, #16, #36; freezing the THRs of #38 and #41; the release and calibration gates (ADR-0005) |
| [#7](https://github.com/bhargavchintam/aureproof/issues/7) | **Provide a provider key.** Put `ANTHROPIC_API_KEY=...` in `~/.aureproof-spike.env`, run `chmod 600` on it, and approve a small budget. | The live Claude Code episode (`spikes/inspect_day2/live.py`), the single-shot probe (`aureproof task probe <task> --model <id>`, #44), the real-key digest check (#42), the live slice (#47, [procedure](guides/live-slice.md)) |
| [#32](https://github.com/bhargavchintam/aureproof/issues/32) | **Provision the Linux host** ([guide](guides/linux-host.md)) and run `scripts/check_host.sh` until every line says `PASS`. | Running the Docker lane there (`uv run --extra inspect pytest tests/integration --no-cov`), which qualifies #39, #42 and the THR determinism re-runs on the named host |
| [#33](https://github.com/bhargavchintam/aureproof/issues/33) | **Choose a dedicated, non-personal conduct-report address** (for example, a new mailbox or alias) and confirm that you receive mail sent to it. | Writing it and the reporting procedure into `CODE_OF_CONDUCT.md` |
| [#6](https://github.com/bhargavchintam/aureproof/issues/6) | **Hold 3–5 practitioner interviews** with the kit in [`research/`](research/), and record each one in `notes-template.md`. | The go, narrow or rethink decision that #47 requires |
| [#37](https://github.com/bhargavchintam/aureproof/issues/37) | **Add the PyPI pending publisher** at <https://pypi.org/manage/account/publishing/>. Use project `aureproof`, owner `bhargavchintam`, repository `aureproof`, workflow `release.yml` and environment `pypi`. | The `0.1.0a1` release. The protected `pypi` GitHub environment exists (required reviewer @bhargavchintam, `v*` tags only). Publishing then means bumping the version and publishing a GitHub Release ([releasing guide](guides/releasing.md)) |

## Reviewer packet

The reviewer signs off by commenting on each issue. They check:

1. **Scoring spec (#9):** `specs/scoring/scoring.md`. Rules M1–M9, the
   dispositions and the metrics. Then the open questions at the end of the file,
   and whether `conformance/scoring/v0.1/golden.json` matches the rules by hand.
2. **Task Health Records (#38, #41):** for each of `authz-001`, `path-001` and
   `authz-002`, read `fixtures/oracles/<task>/README.md`, then `labels.json`
   against the code in `fixtures/security/<task>/variants/`. Check that the defect
   is real, the accepted CWEs fit, the decoys are safe, and the known limits are
   stated. Run `uv run aureproof task validate <task>`. Decide whether `authz-002`
   is a separate cluster from `authz-001` (same CWE family, different mechanism).
3. **THR, Decision and Bundle specs (#12, #14, #36):** `specs/thr/`,
   `specs/decision/` and `specs/bundle/`, with their open questions.

When the reviewer signs off, their name goes into each THR's `reviewed_by` and the
records are frozen (ADR-0005).
