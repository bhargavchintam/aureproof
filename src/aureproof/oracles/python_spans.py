# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Read symbol spans and line counts from Python sources (adapter: file I/O).

Feeds ``contracts.labels_lint.lint_labels`` so label drift is caught. Parsing
uses ``ast`` only; nothing is imported or executed.
"""

from __future__ import annotations

import ast
from pathlib import Path

_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _collect(node: ast.AST, prefix: str, spans: dict[str, tuple[int, int]]) -> None:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _DEFS):
            name = f"{prefix}{child.name}"
            spans[name] = (child.lineno, child.end_lineno or child.lineno)
            _collect(child, f"{name}.", spans)


def python_spans(root: Path) -> dict[str, dict[str, tuple[int, int]]]:
    """``{relative path: {qualified symbol: (start, end)}}`` for functions and classes."""
    out: dict[str, dict[str, tuple[int, int]]] = {}
    for path in sorted(root.rglob("*.py")):
        spans: dict[str, tuple[int, int]] = {}
        _collect(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)), "", spans)
        out[path.relative_to(root).as_posix()] = spans
    return out


def line_counts(root: Path) -> dict[str, int]:
    return {
        p.relative_to(root).as_posix(): len(p.read_text(encoding="utf-8").splitlines())
        for p in sorted(root.rglob("*.py"))
    }
