# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Build Croissant 1.1 + RAI metadata for the fixture pack (issue #60).

    uv run python scripts/make_croissant.py            # write fixtures/croissant.json
    uv run python scripts/make_croissant.py --check    # exit 1 on drift

Every fixture file is a FileObject with its SHA-256, so the metadata pins the exact
bytes it describes. The task list is a RecordSet read from fixtures/dataset.json.
The "Croissant" CI workflow validates the result with mlcroissant 1.1.1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
OUT = FIXTURES / "croissant.json"
REPO = "https://github.com/bhargavchintam/aureproof"
CONTEXT = {
    "@language": "en",
    "@vocab": "https://schema.org/",
    "citeAs": "cr:citeAs",
    "column": "cr:column",
    "conformsTo": "dct:conformsTo",
    "cr": "http://mlcommons.org/croissant/",
    "rai": "http://mlcommons.org/croissant/RAI/",
    "data": {"@id": "cr:data", "@type": "@json"},
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    "dct": "http://purl.org/dc/terms/",
    "examples": {"@id": "cr:examples", "@type": "@json"},
    "extract": "cr:extract",
    "field": "cr:field",
    "fileObject": "cr:fileObject",
    "fileProperty": "cr:fileProperty",
    "fileSet": "cr:fileSet",
    "format": "cr:format",
    "includes": "cr:includes",
    "isLiveDataset": "cr:isLiveDataset",
    "jsonPath": "cr:jsonPath",
    "key": "cr:key",
    "md5": "cr:md5",
    "parentField": "cr:parentField",
    "path": "cr:path",
    "recordSet": "cr:recordSet",
    "references": "cr:references",
    "regex": "cr:regex",
    "repeated": "cr:repeated",
    "replace": "cr:replace",
    "sc": "https://schema.org/",
    "separator": "cr:separator",
    "source": "cr:source",
    "subField": "cr:subField",
    "transform": "cr:transform",
}
MEDIA = {".py": "text/x-python", ".md": "text/markdown", ".json": "application/json"}


def _file_object(path: Path) -> dict[str, Any]:
    rel = path.relative_to(FIXTURES).as_posix()
    evaluator_only = rel.startswith("oracles/")
    return {
        "@type": "cr:FileObject",
        "@id": rel,
        "name": rel,
        "description": (
            "Evaluator-only: labels, calibration PoC or notes. Never mounted for an agent."
            if evaluator_only
            else "Agent-visible: the task instruction or one variant's source."
        ),
        "contentUrl": rel,
        "encodingFormat": MEDIA[path.suffix],
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def build() -> dict[str, Any]:
    registry = json.loads((FIXTURES / "dataset.json").read_text(encoding="utf-8"))
    tasks = [t["task_id"] for t in registry["tasks"]]
    files = sorted(
        p
        for task in tasks
        for base in (FIXTURES / "security" / task, FIXTURES / "oracles" / task)
        for p in base.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    distribution = [_file_object(FIXTURES / "dataset.json"), *(_file_object(p) for p in files)]
    distribution[0]["description"] = "Dataset registry: tasks, splits, canaries, exposure."

    def field(name: str, path: str, description: str) -> dict[str, Any]:
        return {
            "@type": "cr:Field",
            "@id": f"tasks/{name}",
            "name": name,
            "description": description,
            "dataType": "sc:Text",
            "source": {"fileObject": {"@id": "dataset.json"}, "extract": {"jsonPath": path}},
        }

    return {
        "@context": CONTEXT,
        "@type": "sc:Dataset",
        "conformsTo": "http://mlcommons.org/croissant/1.1",
        "name": registry["dataset_id"],
        "description": (
            "Self-authored, synthetic vulnerable/repaired Python code pairs for measuring "
            "precision-first security-defect discovery by AI agents, with evaluator-only "
            "labels, calibration PoCs, decoys and canaries. Every task here is public and "
            "therefore a development task. The private held-out assessment split is not "
            "part of this release. Evaluation only: never use it for training."
        ),
        "version": registry["dataset_revision"],
        "datePublished": "2026-10-11",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "url": REPO,
        "creator": {"@type": "sc:Person", "name": "Bindu Bhargava R Chintam", "url": REPO},
        "citeAs": (
            "@software{aureproof, author = {Chintam, Bindu Bhargava R}, title = {Aureproof: "
            "an integrity layer for AI-agent evaluations}, url = {" + REPO + "}, year = {2026}}"
        ),
        "keywords": ["AI evaluation", "security", "benchmark integrity", "synthetic code"],
        "isAccessibleForFree": True,
        "isLiveDataset": False,
        "rai:dataCollection": (
            "Written by hand by the maintainer for this benchmark; not derived from third-party "
            "code, and no real system is targeted. Each pair differs only in one focal "
            "function, which a test enforces."
        ),
        "rai:dataCollectionType": "Manual Human Curation",
        "rai:dataAnnotationProtocol": (
            "Labels name each defect's accepted CWEs, AST-checked site and source anchors, the "
            "focal negative on the repaired variant, and the reviewed-negative scope (decoys). "
            "A calibration PoC demonstrates each defect, and a Task Health Record runs the "
            "required controls (label lint, reference positive, repaired negative, nop, spray "
            "cheat, malformed, calibration PoC) twice. An independent reviewer must sign off "
            "before records are frozen."
        ),
        "rai:annotationsPerItem": "One author; independent review pending (issue #31).",
        "rai:machineAnnotationTools": "None. Labels are hand-written; tools only check them.",
        "rai:dataUseCases": (
            "Validating AI security-review agents and the Aureproof evaluation pipeline on a "
            "small, controlled suite. Not for training, fine-tuning or retrieval corpora."
        ),
        "rai:dataLimitations": (
            "Synthetic and small (three pairs at revision 0.1.0-dev): it measures controlled "
            "skills, not real-world capability, and results do not generalize to a wider "
            "population of code. Public tasks may be contaminated, so they are development "
            "tasks only."
        ),
        "rai:dataBiases": (
            "Python only, web-service shaped code, two vulnerability families (access control, "
            "path boundary), written by one author."
        ),
        "rai:personalSensitiveInformation": "None: synthetic code with made-up identifiers.",
        "rai:dataSocialImpact": (
            "The defects are textbook classes in small synthetic services, which gives little "
            "uplift for misuse. The aim is to measure false alarms as well as detection."
        ),
        "rai:dataReleaseMaintenancePlan": (
            "Versioned by dataset_revision with per-task revisions; changes are recorded in "
            "CHANGELOG.md. A private held-out assessment split lives in a private repository, "
            "published only after its assessment is complete. Public tasks never move into it."
        ),
        "distribution": distribution,
        "recordSet": [
            {
                "@type": "cr:RecordSet",
                "@id": "tasks",
                "name": "tasks",
                "description": "One record per registered task.",
                "field": [
                    field("task_id", "$.tasks[*].task_id", "Task identifier."),
                    field("split", "$.tasks[*].split", "development or assessment."),
                    field("task_revision", "$.tasks[*].task_revision", "Task revision."),
                    field("canary", "$.tasks[*].canary", "Public canary GUID in every file."),
                ],
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = json.dumps(build(), indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("fixtures/croissant.json drifted: run scripts/make_croissant.py", file=sys.stderr)
            return 1
        print("fixtures/croissant.json matches")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
