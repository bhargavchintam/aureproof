# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Every Eval Ever exporter, pinned to 0.3.0 (issue #59; plan §8 Eval interchange).

One sealed run bundle (one system configuration) becomes one EEE aggregate
record: the model from ``system.json``, and one ``evaluation_results`` entry per
metric with its exact numerator and denominator kept as string details. The
bundle's identities travel in ``source_metadata.additional_details``.
``from_eee`` reads them back. EEE has no place for the rest, which is reported as
losses: per-finding verdicts, the journal, Task Health Records, decisions,
adjudications and signatures. An EEE record is an interchange copy. It carries
no seal and no signature, and it says so. Integrity claims stay with the
source bundle.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from aureproof.bundle.canonical import digest_ref
from aureproof.bundle.models import SEAL
from aureproof.bundle.run import METRICS, PROTOCOL, SYSTEM
from aureproof.contracts import SystemSpec
from aureproof.contracts.decision import DecisionProtocol
from aureproof.contracts.strict_json import loads_strict

EEE_VERSION = "0.3.0"
# sha256 of every_eval_ever 0.3.0's schemas/eval.schema.json (vendored beside this file)
EEE_SCHEMA_SHA256 = "c9c6195aec8a9dfa0b2aba4924ac1aa8a184c9d8ca97cee778cb531088e39b48"
SCHEMA_FILE = "schemas/eee-0.3.0-eval.schema.json"
PREFIX = "aureproof."
HIGHER_IS_BETTER = frozenset(
    {
        "known_defect_recall",
        "adjudicated_precision",
        "strict_confirmed_yield",
        "operational_completion",
    }
)
INTEGRITY_NOTE = (
    "This record carries no seal or signature. Verify the source bundle "
    "(aureproof validate --require-signature) before relying on it."
)
LOSSES = (
    "per-finding verdicts and dispositions are not exported (EEE aggregate records)",
    "the attempt journal, model and tool observations are not exported",
    "Task Health Records and decisions have no EEE field (proposed upstream, plan §9.4)",
    "adjudications are not exported; metrics are pre-adjudication",
    "the bundle seal and signature are not carried; only the seal digest is referenced",
)


@dataclass(frozen=True)
class Export:
    record: dict[str, Any]
    losses: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Imported:
    identities: dict[str, str]
    metrics: dict[str, tuple[int, int, float | None]]  # name -> (numerator, denominator, value)
    model: str


def to_eee(files: Mapping[str, bytes], *, retrieved_timestamp: str, organization: str) -> Export:
    """The EEE record for one sealed run bundle. Timestamp: Unix epoch seconds, as text."""
    seal = loads_strict(files[SEAL], i_json=True)
    predicate = seal["predicate"]
    system = SystemSpec.model_validate(loads_strict(files[SYSTEM], i_json=True))
    metrics_doc = loads_strict(files[METRICS], i_json=True)
    cohort = str(metrics_doc["cohort"])
    model = system.models["main"]
    # EEE wants "developer/model"; one evaluation per system, so the identity is in the id
    model_id = model.model if "/" in model.model else f"{model.provider}/{model.model}"
    identities = {
        "aureproof_bundle_seal": digest_ref(files[SEAL]),
        "aureproof_bundle_version": str(predicate["bundle_version"]),
        "aureproof_scoring_identity": str(predicate["versions"]["scoring_profile"]),
        "aureproof_system_identity": system.identity,
        "aureproof_cohort": cohort,
        "aureproof_integrity": INTEGRITY_NOTE,
    }
    if PROTOCOL in files:
        protocol = DecisionProtocol.model_validate(loads_strict(files[PROTOCOL], i_json=True))
        identities["aureproof_protocol_identity"] = protocol.identity
    losses = list(LOSSES)
    results = []
    for name, m in sorted(metrics_doc["metrics"].items()):
        if m.get("value") is None:
            losses.append(
                f"{name}: undefined ({m['numerator']}/{m['denominator']}); EEE needs a number"
            )
            continue
        rate = m.get("kind") == "rate"
        results.append(
            {
                "evaluation_result_id": f"{cohort}/{name}",
                "evaluation_name": cohort,
                "source_data": {
                    "dataset_name": cohort,
                    "source_type": "other",
                    "additional_details": {"provider": "aureproof run bundle"},
                },
                "metric_config": {
                    "evaluation_description": f"Aureproof {name} (scoring.md section 6)",
                    "metric_id": PREFIX + name,
                    "metric_name": name,
                    "metric_kind": "rate" if rate else "proportion",
                    "metric_unit": "rate" if rate else "proportion",
                    "lower_is_better": name not in HIGHER_IS_BETTER,
                    "score_type": "continuous",
                    "min_score": 0,
                    "max_score": "Infinity" if rate else 1,
                    "additional_details": {"metric_version": str(m["metric_version"])},
                },
                "score_details": {
                    "score": m["value"],
                    "details": {
                        "numerator": str(m["numerator"]),
                        "denominator": str(m["denominator"]),
                    },
                    "uncertainty": {"num_samples": m["denominator"]},
                },
            }
        )
    record = {
        "schema_version": EEE_VERSION,
        "evaluation_id": f"{cohort}/{model_id}/{system.identity[7:19]}/{retrieved_timestamp}",
        "retrieved_timestamp": retrieved_timestamp,
        "source_metadata": {
            "source_name": "Aureproof sealed run bundle",
            "source_type": "evaluation_run",
            "source_organization_name": organization,
            "evaluator_relationship": "third_party",
            "additional_details": identities,
        },
        "eval_library": {
            "name": "aureproof",
            "version": str(predicate["generator"]["version"]),
            "additional_details": {
                "runner": f"{system.runner.name} {system.runner.version}",
                "subject": f"{system.subject.name} {system.subject.version}",
            },
        },
        "model_info": {
            "name": model.model,
            "id": model_id,
            "developer": model.provider,
            "additional_details": {
                "deployment_type": "externally_managed"
                if model.provider not in ("mockllm",)
                else "unknown",
                "model_availability": "unknown",
                "protocol": model.protocol,
            },
        },
        "evaluation_results": results,
    }
    return Export(record, losses)


def from_eee(record: Mapping[str, Any]) -> Imported:
    """Read back what an Aureproof export carries; refuses other versions and sources."""
    if record.get("schema_version") != EEE_VERSION:
        raise ValueError(f"EEE {record.get('schema_version')!r} is not the pinned {EEE_VERSION}")
    if record.get("eval_library", {}).get("name") != "aureproof":
        raise ValueError("not an Aureproof export")
    details = dict(record["source_metadata"]["additional_details"])
    metrics = {}
    for result in record["evaluation_results"]:
        metric_id = result["metric_config"]["metric_id"]
        if not metric_id.startswith(PREFIX):
            continue
        d = result["score_details"]["details"]
        metrics[metric_id.removeprefix(PREFIX)] = (
            int(d["numerator"]),
            int(d["denominator"]),
            result["score_details"]["score"],
        )
    return Imported(details, metrics, record["model_info"]["id"])
