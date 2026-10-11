# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""File docs/backlog/issues.toml to GitHub as labels, milestones, and issues.

Idempotent and safe to re-run:
- labels are upserted (created or updated);
- milestones and issues are matched by title and created only when missing
  (labels and milestone are set at creation; change them on GitHub afterwards);
- issue bodies are re-rendered with dependency issue numbers and updated only
  when they differ, keeping any definition-of-done boxes already ticked.

Dry run by default; pass --apply to make changes. Requires an authenticated `gh`.

    uv run python scripts/file_issues.py
    uv run python scripts/file_issues.py --apply
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any

BACKLOG = Path(__file__).resolve().parents[1] / "docs" / "backlog" / "issues.toml"
FOOTER = (
    "_Filed from `docs/backlog/issues.toml` by `scripts/file_issues.py`. "
    "Edit the TOML and re-run to update._"
)


def gh(*args: str) -> str:
    """Run a gh command and return its stdout."""
    completed = subprocess.run(["gh", *args], check=True, capture_output=True, text=True)
    return completed.stdout


def issue_title(issue: dict[str, Any]) -> str:
    return f"{issue['id']}: {issue['title']}"


def checked_items(body: str) -> set[str]:
    """Return definition-of-done items already ticked in an existing body."""
    return {
        line[len("- [x] ") :].strip()
        for line in body.replace("\r\n", "\n").splitlines()
        if line.lower().startswith("- [x] ")
    }


def render_body(issue: dict[str, Any], numbers: dict[str, int], checked: set[str]) -> str:
    deps = [f"#{numbers[dep]} ({dep})" if dep in numbers else dep for dep in issue["depends"]]
    done = [f"- [{'x' if item in checked else ' '}] {item}" for item in issue["done"]]
    lines = [
        f"**Plan:** `docs/aureproof-plan-v2.md` {issue['plan']} | "
        f"**Estimate:** {issue['estimate']} (planning assumption)",
        "",
        "### Context",
        issue["context"],
        "",
        "### Deliverable",
        issue["deliverable"],
        "",
        "### Definition of done",
        *done,
        "",
        "### Depends on",
        *([f"- {dep}" for dep in deps] or ["- Nothing"]),
        "",
        "---",
        FOOTER,
    ]
    return "\n".join(lines) + "\n"


def normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").strip().splitlines())


def sync_labels(repo: str, backlog: dict[str, Any], apply: bool) -> None:
    existing = {
        item["name"]
        for item in json.loads(
            gh("label", "list", "--repo", repo, "--limit", "500", "--json", "name")
        )
    }
    for label in backlog["label"]:
        print(f"label {'update' if label['name'] in existing else 'create'}: {label['name']}")
        if apply:
            gh(
                "label", "create", label["name"], "--repo", repo,
                "--color", label["color"], "--description", label["description"], "--force",
            )  # fmt: skip


def sync_milestones(repo: str, backlog: dict[str, Any], apply: bool) -> None:
    existing = {
        item["title"]
        for item in json.loads(gh("api", f"repos/{repo}/milestones?state=all&per_page=100"))
    }
    for milestone in backlog["milestone"]:
        if milestone["title"] in existing:
            print(f"milestone exists: {milestone['title']}")
            continue
        print(f"milestone create: {milestone['title']}")
        if apply:
            gh(
                "api", f"repos/{repo}/milestones",
                "-f", f"title={milestone['title']}",
                "-f", f"description={milestone['description']}",
            )  # fmt: skip


def sync_issues(repo: str, backlog: dict[str, Any], apply: bool) -> None:
    listing = gh(
        "issue", "list", "--repo", repo, "--state", "all", "--limit", "1000",
        "--json", "number,title,body",
    )  # fmt: skip
    existing: dict[str, dict[str, Any]] = {item["title"]: item for item in json.loads(listing)}
    numbers: dict[str, int] = {}

    # Pass 1: create missing issues (dependencies that are not yet numbered stay as IDs).
    for issue in backlog["issue"]:
        title = issue_title(issue)
        if title in existing:
            numbers[issue["id"]] = existing[title]["number"]
            continue
        print(f"issue create: {title}")
        if not apply:
            continue
        body = render_body(issue, numbers, checked=set())
        label_args = [arg for label in issue["labels"] for arg in ("--label", label)]
        url = gh(
            "issue", "create", "--repo", repo, "--title", title, "--body", body,
            "--milestone", issue["milestone"], *label_args,
        ).strip()  # fmt: skip
        number = int(url.rstrip("/").rsplit("/", 1)[-1])
        numbers[issue["id"]] = number
        existing[title] = {"number": number, "title": title, "body": body}

    # Pass 2: re-render bodies so every dependency shows its issue number.
    for issue in backlog["issue"]:
        title = issue_title(issue)
        if title not in existing:
            continue
        current = existing[title]["body"] or ""
        body = render_body(issue, numbers, checked=checked_items(current))
        if normalize(body) != normalize(current):
            print(f"issue update body: #{existing[title]['number']} {title}")
            if apply:
                gh("issue", "edit", str(existing[title]["number"]), "--repo", repo, "--body", body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="File the backlog to GitHub.")
    parser.add_argument("--apply", action="store_true", help="make changes (default: dry run)")
    parser.add_argument("--repo", help="owner/name (default: the repository gh resolves here)")
    args = parser.parse_args(argv)

    with BACKLOG.open("rb") as handle:
        backlog = tomllib.load(handle)
    repo = (
        args.repo or gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner").strip()
    )

    print(f"[{'APPLY' if args.apply else 'DRY RUN'}] {repo}")
    sync_labels(repo, backlog, args.apply)
    sync_milestones(repo, backlog, args.apply)
    sync_issues(repo, backlog, args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
