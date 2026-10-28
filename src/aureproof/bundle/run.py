# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Run bundles: seal scored episodes, and re-score them from saved records only.

A run bundle (specs/bundle §3a) adds three members to the core layout:

- ``episodes.json``: one ``EpisodeInput`` per scheduled episode (role ``episodes``);
- ``tasks/<task_id>/labels.json``: the evaluator labels used (role ``labels``);
- the captured submissions, as content-addressed blobs.

``verdicts.json`` and ``metrics.json`` hold the scores. ``rescore`` recomputes them
from the episodes, labels and blobs, and reports whether every byte matches.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import Field, TypeAdapter, ValidationError

from aureproof.bundle.build import Member, build_bundle
from aureproof.bundle.canonical import canonical_json, digest_ref, sha256_hex
from aureproof.bundle.models import BLOB_PREFIX
from aureproof.contracts._base import Contract, NonEmptyStr, NonNegativeInt, Variant
from aureproof.contracts.events import Event, ObservationSource
from aureproof.contracts.labels import LabelSet
from aureproof.contracts.strict_json import JsonInputError, loads_strict
from aureproof.contracts.verdicts import EpisodeSignals
from aureproof.scoring import (
    DISPOSITION_VERSION,
    MATCHER_VERSION,
    METRICS_VERSION,
    EpisodeScore,
    compute_metrics,
    score_episode,
    scoring_identity,
)

EPISODES = "episodes.json"
VERDICTS = "verdicts.json"
METRICS = "metrics.json"
PROTOCOL = "protocol.json"  # live run bundles (specs/bundle §3a)
JOURNAL_EPISODE_PLANNED = "episode_planned"
SYSTEM = "system.json"


class EpisodeInput(Contract):
    episode_id: NonEmptyStr
    task_id: NonEmptyStr
    variant: Variant
    labels: NonEmptyStr  # bundle path of the label set
    agent_view: dict[NonEmptyStr, NonNegativeInt]
    signals: EpisodeSignals
    submission: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")


_EPISODES = TypeAdapter(list[EpisodeInput])


def labels_path(task_id: str) -> str:
    return f"tasks/{task_id}/labels.json"


def thr_path(task_id: str) -> str:
    return f"tasks/{task_id}/thr.json"


def _score_all(
    episodes: Sequence[EpisodeInput],
    labels: Mapping[str, bytes],
    blobs: Mapping[str, bytes],
) -> list[tuple[EpisodeInput, EpisodeScore]]:
    out = []
    for ep in episodes:
        label_set = LabelSet.model_validate_json(labels[ep.labels])
        data = None if ep.submission is None else blobs[ep.submission]
        out.append(
            (
                ep,
                score_episode(
                    data, ep.signals, label_set, variant=ep.variant, agent_view=ep.agent_view
                ),
            )
        )
    return out


def _documents(
    scored: Sequence[tuple[EpisodeInput, EpisodeScore]], cohort: str
) -> tuple[bytes, bytes]:
    verdicts: list[dict[str, Any]] = [
        {
            "episode_id": ep.episode_id,
            "disposition": s.disposition.value,
            "verdicts": None
            if s.verdicts is None
            else [v.model_dump(mode="json", exclude_none=True) for v in s.verdicts],
            "credited": list(s.credited),
            "annotations": list(s.annotations),
            "scoring_identity": s.scoring_identity,
        }
        for ep, s in scored
    ]
    metrics = compute_metrics([s for _, s in scored], cohort=cohort)
    metrics_doc = {
        "cohort": cohort,
        "metrics": {k: m.model_dump(mode="json", exclude_none=True) for k, m in metrics.items()},
    }
    return canonical_json(verdicts), canonical_json(metrics_doc)


def seal_run(
    episodes: Sequence[EpisodeInput],
    labels: Mapping[str, bytes],
    submissions: Sequence[bytes],
    *,
    cohort: str,
    generator: Mapping[str, str],
    completeness: Literal["complete", "redacted"] = "complete",
    prior_events: Sequence[Event] = (),
    extra: Sequence[Member] = (),
) -> dict[str, bytes]:
    """Score every episode and seal the run. Pure: files in, files out.

    ``prior_events`` is the attempt journal of a live run (planning, dispatch,
    tool and model observations, outcomes); the scoring events follow it in one
    hash chain. ``extra`` adds evidence members such as the protocol, the system
    spec and the Task Health Records.
    """
    blobs = {digest_ref(b): b for b in submissions}
    scored = _score_all(episodes, labels, blobs)
    verdicts, metrics = _documents(scored, cohort)
    members = [
        Member(
            EPISODES, canonical_json(_EPISODES.dump_python(list(episodes), mode="json")), "episodes"
        ),
        Member(VERDICTS, verdicts, "verdicts"),
        Member(METRICS, metrics, "metrics"),
        *[Member(path, data, "labels") for path, data in sorted(labels.items())],
        *extra,
    ]
    events = [
        *prior_events,
        *(
            Event(
                seq=len(prior_events) + i,
                episode_id=ep.episode_id,
                actor="aureproof",
                kind="episode_scored",
                observation_source=ObservationSource.CONTROLLER_OBSERVED,
                payload={
                    "disposition": s.disposition.value,
                    "scoring_identity": s.scoring_identity,
                },
                blob_refs=[ep.submission] if ep.submission else [],
            )
            for i, (ep, s) in enumerate(scored)
        ),
    ]
    versions = {
        "matcher": MATCHER_VERSION,
        "disposition": DISPOSITION_VERSION,
        "metrics": METRICS_VERSION,
        "contracts": "0.1",
        "scoring_spec": "0.1",
        "scoring_profile": scoring_identity(),
    }
    return build_bundle(
        members,
        events,
        blobs=list(blobs.values()),
        versions=versions,
        generator=generator,
        completeness=completeness,
    )


@dataclass
class Rescore:
    status: Literal["reproduced", "mismatch", "not_rescorable"]
    problems: list[str] = field(default_factory=list)
    verdicts: Any = None  # recomputed verdicts document
    metrics: Any = None  # recomputed metrics document
    scored: list[tuple[EpisodeInput, EpisodeScore]] = field(default_factory=list)


def rescore(files: Mapping[str, bytes]) -> Rescore:
    """Recompute verdicts and metrics from saved records; compare byte for byte."""
    problems: list[str] = []
    try:
        episodes = _EPISODES.validate_python(loads_strict(files[EPISODES], i_json=True))
        cohort = str(loads_strict(files[METRICS], i_json=True)["cohort"])
    except (KeyError, TypeError, JsonInputError, ValidationError) as exc:
        return Rescore("not_rescorable", [f"episodes or metrics unreadable: {exc}"])
    labels = {ep.labels: files.get(ep.labels) for ep in episodes}
    missing = sorted(p for p, data in labels.items() if data is None)
    if missing:
        return Rescore("not_rescorable", [f"labels not included (redacted?): {', '.join(missing)}"])
    blobs: dict[str, bytes] = {}
    for ep in episodes:
        if ep.submission is not None:
            data = files.get(BLOB_PREFIX + ep.submission.removeprefix("sha256:"))
            if data is None or sha256_hex(data) != ep.submission.removeprefix("sha256:"):
                return Rescore("not_rescorable", [f"{ep.episode_id}: submission blob missing"])
            blobs[ep.submission] = data
    try:
        scored = _score_all(episodes, {p: d for p, d in labels.items() if d is not None}, blobs)
    except ValidationError as exc:
        return Rescore("not_rescorable", [f"labels invalid: {exc.error_count()} errors"])
    verdicts, metrics = _documents(scored, cohort)
    if verdicts != files.get(VERDICTS):
        problems.append("verdicts.json differs from the recomputed verdicts")
    if metrics != files.get(METRICS):
        problems.append("metrics.json differs from the recomputed metrics")
    return Rescore(
        "mismatch" if problems else "reproduced",
        problems,
        loads_strict(verdicts, i_json=True),
        loads_strict(metrics, i_json=True),
        scored,
    )
