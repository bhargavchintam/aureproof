<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Migration vector: labels draft-0 to v0.1

- `input.json`: the authz-001 labels as first committed (`d85a543`), schema
  `aureproof.labels/draft-0`.
- `expected.json`: what `aureproof migrate` must produce.
- `losses.json`: what it declares it could not carry over.
- `hand-migrated-d417444.json`: the same labels as migrated by hand in `d417444`.
  It differs from `expected.json` only by the declared loss: the focal
  negative's source anchor, which a mechanical migration cannot infer.
