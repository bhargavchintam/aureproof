# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Build the comparison-gate examples: one per outcome (issues #50, #53).

    uv run python scripts/make_gate_examples.py            # write
    uv run python scripts/make_gate_examples.py --check    # exit 1 on drift

Each example is a protocol and two live-run-shaped bundles (configurations A and
B) over eight synthetic clusters that reuse the golden ``g1`` labels, so the
per-cluster strict yields, and therefore the exact p-values and intervals, can
be worked out by hand (``expected.json``). The bundles carry the protocol,
system and THR members and planned-episode journal events, so ``aureproof
compare`` checks the full linkage. No code exists behind the synthetic tasks.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from aureproof.bundle.build import Member
from aureproof.bundle.canonical import canonical_json, digest_ref
from aureproof.bundle.run import PROTOCOL, SYSTEM, EpisodeInput, labels_path, seal_run, thr_path
from aureproof.contracts import EpisodeSignals, EpisodeSpec, RunnerOutcome, SystemSpec
from aureproof.contracts.decision import CohortTask, Configurations, DecisionProtocol
from aureproof.contracts.events import Event, ObservationSource
from aureproof.contracts.thr import TaskHealthRecord, thr_digest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "gate"
GOLDEN = ROOT / "conformance" / "scoring" / "v0.1" / "golden.json"
TASKS = [f"s{i}" for i in range(1, 9)]
OK = EpisodeSignals(evidence_complete=True, runner_outcome=RunnerOutcome.OK)

HIT = {
    "cwe": 89,
    "locations": [{"file": "app/orders.py", "symbol": "find_orders"}],
    "description": "query built from request input",
}
FALSE_ALARM = {
    "cwe": 89,
    "locations": [{"file": "app/admin.py", "start_line": 5, "end_line": 6}],
    "description": "looks like a query built from input",
}
# Per side: (vulnerable findings, repaired findings). Strict yield is confirmed / submitted.
HALF = ([HIT, FALSE_ALARM], [])  # 1/2
ONE = ([HIT], [])  # 1/1
QUARTER = ([HIT, FALSE_ALARM, FALSE_ALARM], [FALSE_ALARM])  # 1/4
SCENARIOS: dict[str, list[tuple[Any, Any]]] = {
    "pass": [(HALF, ONE)] * 8,  # each cluster: B - A = +1/2
    "fail": [(ONE, QUARTER)] * 8,  # each cluster: B - A = -3/4
    "inconclusive": [(HALF, ONE)] * 4 + [(ONE, HALF)] * 4,  # +1/2 four times, -1/2 four times
}
EXPECTED = {
    "pass": {
        "outcome": "pass",
        "mean_difference": "1/2",
        "p_value_two_sided": "1/128",
        "why": "all 8 differences are +1/2; only the all-plus and all-minus sign flips reach "
        "|mean| >= 1/2, so p = 2/256",
    },
    "fail": {
        "outcome": "fail",
        "mean_difference": "-3/4",
        "p_value_two_sided": "1/128",
        "why": "all 8 differences are -3/4; p = 2/256 as above",
    },
    "inconclusive": {
        "outcome": "inconclusive",
        "mean_difference": "0/1",
        "p_value_two_sided": "1/1",
        "why": "four +1/2 and four -1/2 average to 0, and every sign flip has |mean| >= 0",
    },
}


def _instance(path: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((ROOT / path).read_text(encoding="utf-8"))["instance"]
    return data


SYSTEMS = {
    "A": SystemSpec.model_validate(
        _instance("conformance/contracts/v0.1/system-spec/valid/reference-react.json")
    ),
    "B": SystemSpec.model_validate(
        _instance("conformance/contracts/v0.1/system-spec/valid/claude-code-closed-world.json")
    ),
}


def _thr(task: str) -> TaskHealthRecord:
    data = _instance("conformance/thr/v0.1/valid/healthy.json")
    data["task"] = {
        "task_id": task,
        "task_revision": "0.1.0",
        "task_identity": digest_ref({"synthetic_task": task}),
    }
    data["known_limits"] = ["Synthetic example task: no code exists behind it."]
    return TaskHealthRecord.model_validate(data)


def _protocol(name: str, thrs: dict[str, TaskHealthRecord]) -> DecisionProtocol:
    return DecisionProtocol(
        protocol_version="0.1",
        name=f"gate-example-{name}",
        cohort=[
            CohortTask(
                task_identity=thrs[t].task.task_identity,
                thr_digest=thr_digest(thrs[t]),
                cluster_id=t,
            )
            for t in TASKS
        ],
        configurations=Configurations(A=SYSTEMS["A"].identity, B=SYSTEMS["B"].identity),
        repetitions=1,
        margin=0.05,
    )


def _bundle(
    side: str, protocol: DecisionProtocol, thrs: dict[str, TaskHealthRecord], plan: list[Any]
) -> dict[str, bytes]:
    labels = json.loads(GOLDEN.read_text(encoding="utf-8"))["label_sets"]["g1"]
    system = SYSTEMS[side]
    episodes, submissions, events = [], [], []
    for task, sides in zip(TASKS, plan, strict=True):
        findings = sides[0] if side == "A" else sides[1]
        for variant, found in zip(("vulnerable", "repaired"), findings, strict=True):
            spec = EpisodeSpec.plan(
                task=thrs[task].task.task_identity,
                variant=variant,  # type: ignore[arg-type]
                system=system.identity,
                protocol=protocol.identity,
                repetition=0,
            )
            data = json.dumps(found).encode()
            submissions.append(data)
            events.append(
                Event(
                    seq=len(events),
                    episode_id=spec.episode_id,
                    actor="aureproof",
                    kind="episode_planned",
                    observation_source=ObservationSource.CONTROLLER_OBSERVED,
                    payload={"episode": spec.model_dump(mode="json")},
                )
            )
            episodes.append(
                EpisodeInput(
                    episode_id=spec.episode_id,
                    task_id=task,
                    variant=variant,  # type: ignore[arg-type]
                    labels=labels_path(task),
                    agent_view=labels["agent_view"][variant],
                    signals=OK,
                    submission=digest_ref(data),
                )
            )
    extra = [
        Member(PROTOCOL, canonical_json(protocol.model_dump(mode="json")), "protocol"),
        Member(SYSTEM, canonical_json(system.model_dump(mode="json", by_alias=True)), "system"),
        *(
            Member(thr_path(t), canonical_json(thrs[t].model_dump(mode="json")), "task_health")
            for t in TASKS
        ),
    ]
    return seal_run(
        episodes,
        {labels_path(t): canonical_json(labels) for t in TASKS},
        submissions,
        cohort=protocol.name,
        generator={"name": "aureproof", "version": "gate-example"},
        prior_events=events,
        extra=extra,
    )


def build() -> dict[str, bytes]:
    """Every example file, keyed by its path under examples/gate."""
    thrs = {t: _thr(t) for t in TASKS}
    files: dict[str, bytes] = {}
    for name, plan in SCENARIOS.items():
        protocol = _protocol(name, thrs)
        files[f"{name}/{PROTOCOL}"] = canonical_json(protocol.model_dump(mode="json"))
        files[f"{name}/expected.json"] = canonical_json(EXPECTED[name])
        for side in ("A", "B"):
            for path, data in _bundle(side, protocol, thrs, plan).items():
                files[f"{name}/{side.lower()}/{path}"] = data
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = build()
    on_disk = (
        {p.relative_to(OUT).as_posix(): p.read_bytes() for p in OUT.rglob("*") if p.is_file()}
        if OUT.exists()
        else {}
    )
    if args.check:
        if on_disk != files:
            print("examples/gate drifted: run scripts/make_gate_examples.py", file=sys.stderr)
            return 1
        print(f"examples/gate: {len(files)} files match")
        return 0
    for path, data in files.items():
        target = OUT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(f"wrote {len(files)} files under {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
