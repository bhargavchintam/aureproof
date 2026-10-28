# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Explicit artifact migrations (issue #58; specs/COMPATIBILITY.md rule 2). Pure.

A migration reads one record version and returns a new record of the next
version, plus the losses it could not carry over. It never edits its input.
Only the migrations registered here exist; anything else is refused by name.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from aureproof.contracts.labels import LabelSet

LABELS_DRAFT_0 = "aureproof.labels/draft-0"
LABELS_V0_1 = "aureproof.labels/v0.1"


class MigrationError(ValueError):
    """No registered migration applies, or the input is not what it claims to be."""


@dataclass(frozen=True)
class Migrated:
    record: dict[str, Any]
    source_version: str
    target_version: str
    losses: list[str]


def _labels_draft_0(data: dict[str, Any]) -> Migrated:
    out = copy.deepcopy(data)
    out["schema"] = LABELS_V0_1
    losses: list[str] = []
    for defect in out.get("defects", []):
        if "variant" not in defect:
            raise MigrationError(f"{defect.get('defect_id')}: draft-0 defects have `variant`")
        defect["variants"] = [defect.pop("variant")]
    focal = out.get("focal_negative")
    if focal is not None:
        if "anchor" not in focal:
            raise MigrationError("draft-0 focal_negative has a single `anchor`")
        anchor = dict(focal.pop("anchor"))
        anchor.setdefault("role", "site")
        focal["anchors"] = [anchor]
        if focal.pop("expected", "refuted") != "refuted":
            raise MigrationError("a draft-0 focal negative is always expected to be refuted")
        losses.append(
            "focal_negative: draft-0 had only the site anchor. v0.1 lists every anchor of "
            "the repaired defect; add its source or sink anchors by hand, or a source-end "
            "finding on the repaired variant stays unresolved instead of refuted"
        )
    LabelSet.model_validate(out)  # the result must be a valid v0.1 label set
    return Migrated(out, LABELS_DRAFT_0, LABELS_V0_1, losses)


MIGRATIONS: dict[str, Callable[[dict[str, Any]], Migrated]] = {
    LABELS_DRAFT_0: _labels_draft_0,
}


def migrate(data: Any) -> Migrated:
    """Migrate one record by its declared version; refuse unknown and current versions."""
    if not isinstance(data, dict):
        raise MigrationError("a record must be a JSON object")
    version = data.get("schema")
    if version == LABELS_V0_1:
        raise MigrationError(f"{version} is already the current version; nothing to migrate")
    step = MIGRATIONS.get(str(version))
    if step is None:
        known = ", ".join(sorted(MIGRATIONS))
        raise MigrationError(f"no migration from {version!r} (supported: {known})")
    return step(data)
