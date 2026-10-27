# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Label lint L1-L4 (specs/scoring/scoring.md §2.2; THR control ``label_lint``).

Pure: callers supply what the agent sees (``agent_views``: path -> line count)
and, to catch drift, the real symbol spans (path -> symbol -> (start, end)),
which an adapter reads from the code (``aureproof.oracles.python_spans``).
"""

from __future__ import annotations

from collections.abc import Mapping

from aureproof.contracts.labels import Anchor, LabelSet

Spans = Mapping[str, Mapping[str, tuple[int, int]]]


def _final(symbol: str) -> str:
    return symbol.rsplit(".", 1)[-1]


def lint_labels(
    labels: LabelSet,
    agent_views: Mapping[str, Mapping[str, int]],
    spans: Mapping[str, Spans] | None = None,
) -> list[str]:
    """Problems found, each prefixed with its rule (``L1``…``L4``); empty means clean."""
    problems: list[str] = []
    anchored: list[tuple[str, Anchor]] = [
        (variant, a) for d in labels.defects for variant in d.variants for a in d.anchors
    ]
    if labels.focal_negative is not None:
        fn = labels.focal_negative
        anchored += [(fn.variant, a) for a in fn.anchors]

    # L1: within a file, a final dotted component names exactly one symbol.
    owners: dict[tuple[str, str], str] = {}
    named = [(a.file, a.symbol) for _, a in anchored]
    named += [(s.file, s.symbol) for s in labels.reviewed_negative_scope if s.symbol]
    for file, symbol in named:
        if owners.setdefault((file, _final(symbol)), symbol) != symbol:
            problems.append(f"L1 {file}: {symbol!r} and {owners[(file, _final(symbol))]!r} collide")

    for variant, anchor in anchored:
        where = f"{variant}:{anchor.file}::{anchor.symbol}"
        view = agent_views.get(variant, {})
        # L3: the anchor exists in that variant's view, within the file, and (when spans
        # are supplied) its line range is the symbol's real span: drift is rejected.
        if anchor.file not in view:
            problems.append(f"L3 {where}: file not in the agent view")
            continue
        start, end = anchor.line_range
        if end > view[anchor.file]:
            problems.append(f"L3 {where}: lines {start}-{end} beyond end of file")
        if spans is not None:
            real = spans.get(variant, {}).get(anchor.file, {}).get(anchor.symbol)
            if real is None:
                problems.append(f"L3 {where}: symbol not found in the code")
            elif real != (start, end):
                problems.append(f"L3 {where}: label {start}-{end} drifted from code {real}")
        # L2: no anchor inside reviewed-negative scope for the same variant.
        for scope in labels.reviewed_negative_scope:
            if scope.file != anchor.file:
                continue
            if scope.symbol is None or _final(scope.symbol) == _final(anchor.symbol):
                problems.append(f"L2 {where}: anchor lies inside reviewed-negative scope")

    for scope in labels.reviewed_negative_scope:
        for variant, view in agent_views.items():
            if scope.file not in view:
                problems.append(f"L3 {variant}:{scope.file}: reviewed scope file not in view")

    # L4: every defect accepts at least one CWE (the LabelSet model also enforces it).
    problems += [
        f"L4 {d.defect_id}: no accepted CWE" for d in labels.defects if not d.accepted_cwes
    ]
    return problems
