<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Security Policy

## Reporting a vulnerability

**Do not open a public issue for a security problem.**

Report privately through GitHub's **[Report a vulnerability](https://github.com/bhargavchintam/aureproof/security/advisories/new)**
(Security → Advisories), which opens a private advisory with the maintainers.

Please include a description, affected version or commit, reproduction steps,
and impact. Do not include working exploit code for an unpatched third-party
system in the report body.

## Our commitment (targets, pre-1.0)

- Acknowledge within **7 days**.
- Provide an assessment and a plan within **30 days**.
- Coordinate a fix and disclosure, by default within **90 days** of the report.

These are goodwill targets for a pre-alpha, solo-maintained project, not a
contractual SLA.

## Scope

Aureproof evaluates agents that may handle untrusted code, and its own grader
and controller process attacker-influenced inputs. In scope: isolation or
trust-boundary escapes (grading forgery, label leakage, sandbox egress,
artifact path traversal), evidence-integrity defects (unsigned or forgeable
bundles, undetectable journal truncation), and supply-chain issues.

## If an agent finds a real vulnerability in third-party code

From v0.2 onward, evaluated agents may surface real defects. Report these
privately to the affected project's maintainers and follow their disclosure
process. Do not publish details or exploit code until the issue is fixed. See
[`RESPONSIBLE_USE.md`](RESPONSIBLE_USE.md).
