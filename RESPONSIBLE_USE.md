<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Responsible Use

Aureproof evaluates AI agents on security tasks. That is dual-use, so the
project holds itself to clear limits. These rules are enforced by review and,
where possible, by tests and CI.

## Authorization

- Evaluate agents only against targets that are **self-authored or that you are
  explicitly authorized to test**. Do not point fixtures at third-party live
  systems, networks, or accounts.
- Provider usage policies prohibit discovering or exploiting vulnerabilities
  **without authorization** (e.g. Anthropic's Usage Policy). Synthetic,
  self-authored fixtures with no network access keep evaluation inside bounds.

## Fixtures and data

- v0.1 fixtures are **synthetic and self-authored**. Each ships with a canary
  identifier and a task-health record.
- Real-CVE material (v0.2+) comes only from already-public upstream benchmarks,
  is stored in restricted bundles, and is never redistributed without checking
  the upstream license and terms.
- Public reports **summarize**; they do not ship working exploit code for
  unpatched issues.

## Provider terms

- Evaluation transcripts and datasets are **for evaluation only, not for
  training** competing models — consistent with Anthropic and OpenAI terms.
  Dataset cards state this, and fixtures carry canaries.
- Name models **factually**; do not imply endorsement or use provider logos.
- Never retry or reframe a request to bypass a provider's safety refusal.
  Record it as a `safety_refusal` outcome instead (plan v2 §5.5).

## Isolation

- Evaluated agents run with **no network egress** except the metered model
  proxy. Grading materials (labels, calibration PoCs) never enter the agent's
  build context.
- Verdicts are computed in the trusted controller and are never read from files
  that agent-submitted or agent-executed code can write.

## Disclosure

If an evaluation surfaces a real vulnerability in third-party code, follow the
coordinated process in [`SECURITY.md`](SECURITY.md): report privately upstream,
and do not publish until it is fixed.
