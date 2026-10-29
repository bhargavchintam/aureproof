<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Architecture Decision Records

Short records of significant, hard-to-reverse decisions. Format: a lightweight
[MADR](https://adr.github.io/madr/). Statuses: `proposed`, `accepted`,
`superseded by ADR-XXXX`, `deprecated`.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-narrow-first-release-claim.md) | Narrow the first-release claim to security discovery | accepted |
| [0002](0002-runner-inspect-first.md) | Inspect AI as the first runner; Harbor in v0.2 | accepted (Day-2 spike) |
| [0003](0003-aureproof-owns-attempts.md) | Aureproof owns attempt identity and retries | accepted (Day-2 spike) |
| [0004](0004-oracle-is-a-pure-label-matcher.md) | The v0.1 oracle is a deterministic label matcher | accepted |
| [0005](0005-second-reviewer-required.md) | A second reviewer is required for gates | accepted, amended 2026-10-29 (maintainer self-review, disclosed) |
| [0006](0006-primary-metric-strict-confirmed-yield.md) | Strict confirmed yield is the primary metric | accepted |
| [0007](0007-external-agent-and-interface.md) | External agent, protocol, interface modes, hosted tools and budgets | accepted |

## Template

```markdown
# ADR-XXXX: <title>

- Status: proposed | accepted | superseded by ADR-YYYY | deprecated
- Date: YYYY-MM-DD
- Deciders: <who>

## Context
<forces, constraints, verified facts>

## Decision
<what we will do>

## Consequences
<what becomes easier, harder, and what we must revisit>
```
