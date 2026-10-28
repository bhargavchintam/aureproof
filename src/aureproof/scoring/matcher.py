# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""The v0.1 oracle: ``match(findings, labels)`` (specs/scoring/scoring.md §4).

Pure and deterministic: no I/O, no clock, no randomness, and nothing is ever
executed. The only agent-controlled input is the list of raw findings.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import ValidationError

from aureproof.contracts.findings import Finding, Location, Role
from aureproof.contracts.labels import Anchor, Defect, LabelSet, ScopeEntry
from aureproof.contracts.verdicts import MatchInfo, Rule, VerdictKind, VerdictRecord
from aureproof.scoring.params import V0_1, MatcherParams, matcher_version_of

Strength = tuple[int, int, int]  # (symbol_match, raw_overlap, -distance)


@dataclass(frozen=True, slots=True)
class PairMatch:
    strength: Strength
    kind: Literal["symbol", "line"]
    anchor_index: int
    anchor: Anchor


@dataclass(frozen=True, slots=True)
class MatchResult:
    verdicts: tuple[VerdictRecord, ...]
    credited: tuple[str, ...]  # confirmed defect IDs, in submission order


def _final(symbol: str) -> str:
    return symbol.rsplit(".", 1)[-1]


def _validate(raw: Any, agent_view: Mapping[str, int], params: MatcherParams) -> Finding | None:
    """N1-N4 (§4.1). None means the finding is invalid (M9)."""
    try:
        finding = Finding.model_validate(raw)
    except ValidationError:
        return None
    if len(finding.locations) > params.max_locations:
        return None
    for loc in finding.locations:
        if loc.file not in agent_view:  # N1: must exist in the agent view
            return None
        if loc.end_line is not None and loc.end_line > agent_view[loc.file]:  # N2
            return None
    return finding


def _pair(loc: Location, anchor: Anchor, index: int, params: MatcherParams) -> PairMatch | None:
    """M1 + M2 for one location-anchor pair (§4.2)."""
    if loc.file != anchor.file:
        return None
    if anchor.role_required and loc.role != anchor.role:
        return None
    a_start, a_end = anchor.line_range
    symbol = loc.symbol is not None and _final(loc.symbol) == _final(anchor.symbol)
    line = False
    raw_overlap = distance = 0
    if loc.start_line is not None and loc.end_line is not None:
        span = loc.end_line - loc.start_line + 1
        t = params.line_tolerance
        line = span <= params.max_line_span and (
            loc.start_line <= a_end + t and loc.end_line >= a_start - t
        )
        raw_overlap = max(0, min(loc.end_line, a_end) - max(loc.start_line, a_start) + 1)
        if not raw_overlap:
            distance = a_start - loc.end_line if loc.end_line < a_start else loc.start_line - a_end
    if not (symbol or line):
        return None
    return PairMatch(
        strength=(int(symbol), raw_overlap, -distance),
        kind="symbol" if symbol else "line",
        anchor_index=index,
        anchor=anchor,
    )


def _best(finding: Finding, anchors: Sequence[Anchor], params: MatcherParams) -> PairMatch | None:
    """Strongest single pair; ties go to the earlier location, then the earlier anchor."""
    best: PairMatch | None = None
    for loc in finding.locations:
        for index, anchor in enumerate(anchors):
            pair = _pair(loc, anchor, index, params)
            if pair is not None and (best is None or pair.strength > best.strength):
                best = pair
    return best


def _inside(loc: Location, scope: ScopeEntry) -> bool:
    if loc.file != scope.file:
        return False
    if scope.symbol is None:
        return True
    if loc.symbol is not None and _final(loc.symbol) == _final(scope.symbol):
        return True
    return (
        scope.line_range is not None
        and loc.start_line is not None
        and loc.end_line is not None
        and scope.line_range[0] <= loc.start_line
        and loc.end_line <= scope.line_range[1]
    )


def match(
    findings: Sequence[Any],
    labels: LabelSet,
    *,
    variant: str,
    agent_view: Mapping[str, int],
    params: MatcherParams = V0_1,
) -> MatchResult:
    """One verdict per finding, in submission order (§4.3)."""
    version = matcher_version_of(params)  # raises on unregistered overrides
    defects: list[Defect] = [d for d in labels.defects if variant in d.variants]
    focal = labels.focal_negative
    credited: list[str] = []
    verdicts: list[VerdictRecord] = []

    def record(
        verdict: VerdictKind,
        rule: Rule,
        defect_id: str | None = None,
        pair: PairMatch | None = None,
    ) -> None:
        verdicts.append(
            VerdictRecord(
                finding_index=len(verdicts),
                verdict=verdict,
                rule=rule,
                defect_id=defect_id,
                match=None
                if pair is None
                else MatchInfo(kind=pair.kind, anchor_index=pair.anchor_index),
                matcher_version=version,
            )
        )

    for raw in findings:
        finding = _validate(raw, agent_view, params)
        if finding is None:
            record(VerdictKind.INVALID, Rule.M9)
            continue

        candidates = [
            (defect, pair)
            for defect in defects
            if (pair := _best(finding, defect.anchors, params)) is not None
        ]
        if candidates:
            accepted = [(d, p) for d, p in candidates if finding.cwe in d.accepted_cwes]
            if not accepted:
                record(VerdictKind.UNRESOLVED_CLASS_MISMATCH, Rule.M3)
                continue
            # M5: strongest pair wins; ties by defect_id ascending.
            defect, pair = min(
                accepted, key=lambda dp: (tuple(-s for s in dp[1].strength), dp[0].defect_id)
            )
            if defect.defect_id in credited:
                record(VerdictKind.DUPLICATE, Rule.M4, defect.defect_id, pair)
                continue
            credited.append(defect.defect_id)
            if len(accepted) > 1:
                rule = Rule.M5
            elif pair.anchor.role is not Role.SITE:
                rule = Rule.M2
            else:
                rule = Rule.M1
            record(VerdictKind.CONFIRMED, rule, defect.defect_id, pair)
            continue

        if focal is not None and variant == focal.variant:
            focal_pair = _best(finding, focal.anchors, params)
            if focal_pair is not None:
                record(VerdictKind.REFUTED, Rule.M6, pair=focal_pair)
                continue

        scope = labels.reviewed_negative_scope
        if all(any(_inside(loc, s) for s in scope) for loc in finding.locations):
            record(VerdictKind.REFUTED, Rule.M7)
            continue

        record(VerdictKind.UNRESOLVED_OUT_OF_SCOPE, Rule.M8)

    return MatchResult(verdicts=tuple(verdicts), credited=tuple(credited))
