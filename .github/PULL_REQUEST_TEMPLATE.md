<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
## What and why

<!-- What does this change do, and which issue/plan item (e.g. AP-0xx) does it serve? -->

## Checklist

- [ ] Commits are signed off (`git commit -s`) per the [DCO](https://developercertificate.org/).
- [ ] `uv run ruff check . && uv run ruff format --check .` passes.
- [ ] `uv run mypy` passes.
- [ ] `uv run lint-imports` passes (no new pure-core → adapter/IO dependency).
- [ ] `uv run pytest` passes; new behavior has a test.
- [ ] License/SPDX headers present (`uvx --with charset-normalizer --from reuse reuse lint`).
- [ ] Docs/CHANGELOG updated if behavior or interfaces changed.
- [ ] For fixtures/tasks: read `RESPONSIBLE_USE.md`; content is self-authored or authorized; a canary is present.

## AI-assistance disclosure

<!-- Required. State whether AI tools substantially drafted this change. The
submitter remains responsible for correctness, licensing, and having run the
tests above. Unverifiable AI-generated submissions may be closed. -->

- [ ] AI tools were used substantially in this change.
- [ ] I have reviewed and verified every line I am submitting.
