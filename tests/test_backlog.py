# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Consistency checks for docs/backlog/issues.toml (the GitHub backlog source)."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest

BACKLOG = Path(__file__).resolve().parents[1] / "docs" / "backlog" / "issues.toml"

# Labels GitHub creates on every new repository; the backlog may use them
# without redefining them.
GITHUB_DEFAULT_LABELS = {
    "bug",
    "documentation",
    "duplicate",
    "enhancement",
    "good first issue",
    "help wanted",
    "invalid",
    "question",
    "wontfix",
}


@pytest.fixture(scope="module")
def backlog() -> dict[str, Any]:
    with BACKLOG.open("rb") as handle:
        return tomllib.load(handle)


def test_issue_ids_and_titles_are_unique(backlog: dict[str, Any]) -> None:
    ids = [issue["id"] for issue in backlog["issue"]]
    titles = [issue["title"] for issue in backlog["issue"]]
    assert len(ids) == len(set(ids))
    assert len(titles) == len(set(titles))


def test_every_issue_label_is_defined(backlog: dict[str, Any]) -> None:
    defined = {label["name"] for label in backlog["label"]} | GITHUB_DEFAULT_LABELS
    for issue in backlog["issue"]:
        missing = set(issue["labels"]) - defined
        assert not missing, f"{issue['id']} uses undefined labels {missing}"


def test_every_issue_milestone_is_defined(backlog: dict[str, Any]) -> None:
    milestones = {milestone["title"] for milestone in backlog["milestone"]}
    for issue in backlog["issue"]:
        assert issue["milestone"] in milestones, f"{issue['id']}: unknown milestone"


def test_dependencies_exist_and_are_acyclic(backlog: dict[str, Any]) -> None:
    graph = {issue["id"]: list(issue["depends"]) for issue in backlog["issue"]}
    for node, deps in graph.items():
        assert node not in deps, f"{node} depends on itself"
        unknown = set(deps) - graph.keys()
        assert not unknown, f"{node} depends on unknown issues {unknown}"

    visiting: set[str] = set()
    finished: set[str] = set()

    def visit(node: str, path: tuple[str, ...]) -> None:
        if node in finished:
            return
        assert node not in visiting, f"dependency cycle: {' -> '.join((*path, node))}"
        visiting.add(node)
        for dep in graph[node]:
            visit(dep, (*path, node))
        visiting.discard(node)
        finished.add(node)

    for node in graph:
        visit(node, ())


def test_every_issue_is_actionable(backlog: dict[str, Any]) -> None:
    for issue in backlog["issue"]:
        for field in ("context", "deliverable", "estimate", "plan"):
            assert str(issue[field]).strip(), f"{issue['id']}: empty {field}"
        assert issue["done"], f"{issue['id']}: no definition-of-done items"
        assert len(issue["labels"]) >= 1
        assert any(label in {"P0", "P1", "P2"} for label in issue["labels"]), (
            f"{issue['id']}: missing a priority label"
        )
