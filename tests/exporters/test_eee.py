# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Every Eval Ever 0.3.0 export and round trip (issue #59).

The schema check here uses the pinned upstream schema, vendored and verified by
digest. The independent consumer, EEE's own validator, runs in the CI job
"EEE consumer" on examples/eee.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest
from typer.testing import CliRunner

from aureproof.bundle.canonical import digest_ref
from aureproof.cli.main import app
from aureproof.exporters import eee
from aureproof.storage import read_bundle

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = Path(eee.__file__).parent / eee.SCHEMA_FILE
BUNDLE = ROOT / "examples" / "gate" / "pass" / "a"
TUTORIAL = ROOT / "examples" / "bundles" / "tutorial-v0.1"
cli = CliRunner()


def _export() -> eee.Export:
    return eee.to_eee(read_bundle(BUNDLE), retrieved_timestamp="1793232000", organization="test")


def test_the_vendored_schema_is_the_pinned_upstream_file() -> None:
    data = SCHEMA.read_bytes()
    assert hashlib.sha256(data).hexdigest() == eee.EEE_SCHEMA_SHA256
    assert json.loads(data)["version"] == eee.EEE_VERSION == "0.3.0"


def test_the_export_validates_against_the_pinned_schema() -> None:
    record = _export().record
    schema = json.loads(SCHEMA.read_text())
    validator = jsonschema.validators.validator_for(schema)  # the draft the schema declares
    validator.check_schema(schema)
    validator(schema).validate(record)
    assert record["schema_version"] == "0.3.0"
    assert record["model_info"]["id"].count("/") == 1  # developer/model


def test_round_trip_preserves_identities_and_exact_counts() -> None:
    files = read_bundle(BUNDLE)
    back = eee.from_eee(_export().record)
    metrics = json.loads(files["metrics.json"])["metrics"]
    defined = {k: m for k, m in metrics.items() if m["value"] is not None}
    assert back.metrics == {
        k: (m["numerator"], m["denominator"], m["value"]) for k, m in defined.items()
    }
    seal = json.loads(files["seal.intoto.json"])["predicate"]
    assert back.identities["aureproof_bundle_seal"] == digest_ref(files["seal.intoto.json"])
    assert back.identities["aureproof_scoring_identity"] == seal["versions"]["scoring_profile"]
    assert back.identities["aureproof_system_identity"].startswith("sha256:")
    assert back.identities["aureproof_protocol_identity"].startswith("sha256:")


def test_unmappable_evidence_is_reported_and_no_integrity_is_claimed() -> None:
    export = _export()
    losses = " ".join(export.losses)
    for word in ("per-finding verdicts", "journal", "Task Health Records", "adjudications", "seal"):
        assert word in losses
    note = export.record["source_metadata"]["additional_details"]["aureproof_integrity"]
    assert "carries no seal or signature" in note


def test_undefined_metrics_are_left_out_and_named() -> None:
    files = read_bundle(BUNDLE)
    metrics = json.loads(files["metrics.json"])["metrics"]
    undefined = sorted(k for k, m in metrics.items() if m["value"] is None)
    export = _export()
    exported = {r["metric_config"]["metric_name"] for r in export.record["evaluation_results"]}
    assert exported.isdisjoint(undefined)
    for name in undefined:
        assert any(loss.startswith(f"{name}: undefined") for loss in export.losses)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"schema_version": "0.2.3"}, "not the pinned"),
        ({"eval_library": {"name": "x"}}, "not an Aureproof"),
    ],
)
def test_import_refuses_other_versions_and_sources(change: dict, message: str) -> None:  # type: ignore[type-arg]
    with pytest.raises(ValueError, match=message):
        eee.from_eee({**_export().record, **change})


def test_cli_exports_a_validated_bundle_and_refuses_others(tmp_path: Path) -> None:
    out = tmp_path / "eee.json"
    args = ["export-eee", str(BUNDLE), "--out", str(out), "--organization", "t"]
    result = cli.invoke(app, [*args, "--timestamp", "1793232000"])
    assert result.exit_code == 0, result.output
    assert "not carried:" in result.output
    assert json.loads(out.read_text()) == _export().record | {
        "source_metadata": {**_export().record["source_metadata"], "source_organization_name": "t"}
    }
    assert cli.invoke(app, [*args, "--timestamp", "now"]).exit_code == 2
    no_system = ["export-eee", str(TUTORIAL), "--out", str(tmp_path / "t.json")]
    no_system += ["--organization", "t", "--timestamp", "1"]
    assert cli.invoke(app, no_system).exit_code == 2  # not a run bundle: no system spec


def test_examples_are_committed_exactly_as_generated() -> None:
    spec = importlib.util.spec_from_file_location("eee_ex", ROOT / "scripts/make_eee_examples.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    out = ROOT / "examples" / "eee"
    on_disk = {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob("*.json")}
    assert module.build() == on_disk and len(on_disk) == 2
