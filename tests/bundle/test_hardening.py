# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Builder invariants and bundle schema publication (issue #35)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from aureproof.bundle import BundleError, Member, build_bundle, canonical_json, validate
from aureproof.bundle.schema import SCHEMA_DIR, export_schemas
from aureproof.contracts import Event

ROOT = Path(__file__).resolve().parents[2]
VERSIONS = {"matcher": "0.1.0"}
GEN = {"name": "aureproof", "version": "test"}


def members(**overrides: Any) -> list[Member]:
    base = {
        "verdicts": Member("verdicts.json", b"[]", "verdicts"),
        "metrics": Member("metrics.json", b"{}", "metrics"),
    }
    base.update(overrides)
    return list(base.values())


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        (
            {
                "members": members(
                    verdicts=Member("verdicts.json", b"[]", "verdicts", mandatory=False)
                )
            },
            "mandatory evidence",
        ),
        ({"members": members(metrics=Member("metrics.json", b"{}", "nonsense"))}, "unknown role"),  # type: ignore[arg-type]
        (
            {"members": members(metrics=Member("metrics.json", b"{}", "metrics", media_type=""))},
            "media_type",
        ),
        ({"generator": {}}, "metadata"),
        ({"generator": {"name": "", "version": "1"}}, "metadata"),
        ({"versions": {"matcher": ""}}, "metadata"),
        ({"completeness": "partial"}, "metadata"),
    ],
)
def test_builder_rejects_invalid_metadata(kwargs: dict[str, Any], match: str) -> None:
    args: dict[str, Any] = {
        "members": members(),
        "events": [],
        "blobs": [],
        "versions": VERSIONS,
        "generator": GEN,
        **kwargs,
    }
    with pytest.raises(BundleError, match=match):
        build_bundle(args.pop("members"), args.pop("events"), **args)


text = st.text(st.characters(blacklist_categories=("Cs",)), max_size=20)
payloads = st.recursive(
    st.none()
    | st.booleans()
    | st.integers(-(2**53) + 1, 2**53 - 1)
    | text
    | st.floats(allow_nan=False, allow_infinity=False),
    lambda children: st.lists(children, max_size=3) | st.dictionaries(text, children, max_size=3),
    max_leaves=10,
)


@settings(max_examples=150, deadline=None)
@given(st.lists(st.tuples(text.filter(bool), payloads), max_size=6))
def test_every_successfully_built_bundle_validates(events: list[tuple[str, Any]]) -> None:
    evs = [
        Event(
            seq=i,
            episode_id="e",
            actor="runner",
            kind=kind or "k",
            observation_source="controller_observed",
            payload={"v": payload},
        )
        for i, (kind, payload) in enumerate(events)
    ]
    files = build_bundle(members(), evs, blobs=[], versions=VERSIONS, generator=GEN)
    report = validate(files)
    assert report.valid, report.problems()


def test_committed_bundle_schemas_match_the_models() -> None:
    """Run `uv run python scripts/export_schemas.py` after changing a bundle record."""
    on_disk = {
        p.name.removesuffix(".schema.json"): json.loads(p.read_text(encoding="utf-8"))
        for p in (ROOT / SCHEMA_DIR).glob("*.schema.json")
    }
    assert on_disk == export_schemas()


def test_built_manifest_and_seal_conform_to_the_published_schemas() -> None:
    from jsonschema import Draft202012Validator

    files = build_bundle(members(), [], blobs=[], versions=VERSIONS, generator=GEN)
    for name, path in (("manifest", "manifest.json"), ("seal-statement", "seal.intoto.json")):
        schema = json.loads((ROOT / SCHEMA_DIR / f"{name}.schema.json").read_text("utf-8"))
        assert not list(Draft202012Validator(schema).iter_errors(json.loads(files[path])))
    assert canonical_json(json.loads(files["manifest.json"])) == files["manifest.json"]


@pytest.mark.parametrize(
    "payload", [{"x": float("nan")}, {"x": float("inf")}, {"x": 2**60}, {"x": "\ud800"}]
)
def test_events_reject_values_without_an_rfc8785_form(payload: dict[str, Any]) -> None:
    """Never silently converted to null or a lossy value (issue #35)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Event(
            seq=0,
            episode_id="e",
            actor="a",
            kind="k",
            observation_source="controller_observed",
            payload=payload,
        )
