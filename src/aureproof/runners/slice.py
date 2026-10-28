# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""A protocol-bound run, sealed as one evidence bundle (issue #47, the M2 chain).

Adapter (file I/O; the runner does the process and network work). Before any
episode is dispatched, the run is checked against its Decision Protocol: the
runner's system must be configuration A or B, and every cohort task must match
a registered fixture by identity and come with the healthy Task Health Record
the protocol names by digest. Each episode then goes through the orchestrator,
and one bundle seals the chain: protocol, system spec and THRs as members, the
attempt journal (dispatch, model and tool observations, outcomes), the captured
submissions, and the controller's verdicts. ``aureproof validate`` and
``aureproof score --offline`` check it without live inference.
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from aureproof import __version__
from aureproof.bundle.build import Member
from aureproof.bundle.canonical import canonical_json
from aureproof.bundle.run import PROTOCOL, SYSTEM, EpisodeInput, labels_path, seal_run, thr_path
from aureproof.contracts import EpisodeSpec, LabelSet, SystemSpec, TaskSpec
from aureproof.contracts._base import Variant
from aureproof.contracts.decision import DecisionProtocol
from aureproof.contracts.thr import HealthStatus, TaskHealthRecord, thr_digest
from aureproof.oracles.calibration import Paths, registry, task_spec
from aureproof.oracles.python_spans import line_counts
from aureproof.runners.orchestrate import run_episode
from aureproof.runners.port import AttemptRequest, Runner
from aureproof.storage import BlobStore
from aureproof.storage.ledger_store import AttemptLedgerStore

VARIANTS: tuple[Variant, ...] = ("vulnerable", "repaired")


class SliceError(ValueError):
    """The run does not match its protocol; nothing was dispatched."""


class SystemRunner(Runner, Protocol):
    def system_spec(self) -> SystemSpec: ...


@dataclass(frozen=True)
class Planned:
    task: TaskSpec
    thr: TaskHealthRecord


def plan(
    root: Path,
    protocol: DecisionProtocol,
    thrs: Sequence[TaskHealthRecord],
    system_identity: str,
) -> list[Planned]:
    """Check the run against the protocol, and return its tasks in cohort order."""
    if system_identity not in (protocol.configurations.A, protocol.configurations.B):
        raise SliceError(f"system {system_identity} is neither configuration A nor B")
    registered: dict[str, TaskSpec] = {}
    for entry in registry(root).tasks:
        registered_spec = task_spec(root, entry.task_id)
        registered[registered_spec.identity] = registered_spec
    by_digest = {thr_digest(t): t for t in thrs}
    planned = []
    for cohort_task in protocol.cohort:
        spec = registered.get(cohort_task.task_identity)
        if spec is None:
            raise SliceError(f"no registered fixture has identity {cohort_task.task_identity}")
        thr = by_digest.get(cohort_task.thr_digest)
        if thr is None:
            raise SliceError(f"{spec.task_id}: no THR given with digest {cohort_task.thr_digest}")
        if thr.task.task_identity != spec.identity:
            raise SliceError(f"{spec.task_id}: the THR describes another task identity")
        if thr.status is not HealthStatus.HEALTHY:
            raise SliceError(f"{spec.task_id}: the THR is {thr.status.value}, not healthy")
        planned.append(Planned(spec, thr))
    return planned


def run_slice(
    root: Path,
    protocol: DecisionProtocol,
    thrs: Sequence[TaskHealthRecord],
    runner: SystemRunner,
    *,
    work: Path | None = None,
) -> dict[str, bytes]:
    """Run every planned episode and return the sealed bundle's files."""
    system = runner.system_spec()
    planned = plan(root, protocol, thrs, system.identity)
    with tempfile.TemporaryDirectory() as tmp:
        base = work if work is not None else Path(tmp)
        store = AttemptLedgerStore(base / "run")
        blobs = BlobStore(base / "cas")
        episodes: list[EpisodeInput] = []
        submissions: list[bytes] = []
        labels: dict[str, bytes] = {}
        for item in planned:
            task = item.task
            label_bytes = (Paths(root, task.task_id).oracles / "labels.json").read_bytes()
            label_set = LabelSet.model_validate_json(label_bytes)
            labels[labels_path(task.task_id)] = label_bytes
            for variant in VARIANTS:
                view = line_counts(root / task.agent_views[variant].root)
                for repetition in range(protocol.repetitions):
                    episode = EpisodeSpec.plan(
                        task=task.identity,
                        variant=variant,
                        system=system.identity,
                        protocol=protocol.identity,
                        repetition=repetition,
                    )
                    run = run_episode(
                        store,
                        blobs,
                        runner,
                        AttemptRequest(episode, "", task, system, root, variant),
                        label_set,
                        view,
                    )
                    if run.submission is not None:
                        submissions.append(blobs.get(run.submission))
                    episodes.append(
                        EpisodeInput(
                            episode_id=run.episode_id,
                            task_id=task.task_id,
                            variant=variant,
                            labels=labels_path(task.task_id),
                            agent_view=view,
                            signals=run.signals,
                            submission=run.submission,
                        )
                    )
        extra = [
            Member(PROTOCOL, canonical_json(protocol.model_dump(mode="json")), "protocol"),
            Member(SYSTEM, canonical_json(system.model_dump(mode="json", by_alias=True)), "system"),
            *(
                Member(
                    thr_path(p.task.task_id),
                    canonical_json(p.thr.model_dump(mode="json")),
                    "task_health",
                )
                for p in planned
            ),
        ]
        return seal_run(
            episodes,
            labels,
            submissions,
            cohort=protocol.name,
            generator={"name": "aureproof", "version": __version__},
            prior_events=store.journal.events,
            extra=extra,
        )
