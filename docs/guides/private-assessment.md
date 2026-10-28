<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Private assessment repository (maintainer)

Issue #45. The held-out assessment split must never be public before the authorized
results publication.

## Setup (account actions; maintainer only)

1. A **private** repository `bhargavchintam/aureproof-assessment` (created 2026-10-28).
   - Access: the maintainer and the independent reviewer (#31) only.
   - No forks, no GitHub Pages, no public Actions logs that could print task content.
2. Mirror the public layout. The build contexts stay separated exactly as in the public
   repository:
   - `fixtures/security/<task>/`: agent-visible material only;
   - `fixtures/oracles/<task>/`: labels and calibration PoCs, never mounted for an agent;
   - `fixtures/dataset.json`: the same registry schema (`aureproof.contracts.dataset`),
     with every task registered as `split: assessment`, `private` exposure only, and its
     public and oracle canaries. The schema rejects an assessment task with public exposure.
3. Copy `tests/test_dataset_registry.py` into it, so the same canary checks run there.

## Before the assessment

1. For every assessment task, compute its `TaskSpec.identity`.
2. In a **public** PR, add `{task_identity, registered_at}` to `assessment` in this
   repository's `fixtures/dataset.json`, and bump `dataset_revision`. Membership is now
   fixed and timestamped, but no content is revealed.
3. The signed Decision Protocol (#14, #46, #52) references those same identities.

## After the authorized publication

Publish the assessment tasks with the results. Record their new public exposure in the
registry; from then on they are development tasks.
