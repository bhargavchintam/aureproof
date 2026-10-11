# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Aureproof command-line entry point.

Day-1 scaffold: only `--version` is wired. The `validate`, `score`, `report`,
`compare`, `gate`, `task validate`, `adjudicate`, and `migrate` subcommands are
added across M1-M3 (see docs/aureproof-plan-v2.md §3.9, §11).
"""

from __future__ import annotations

import typer

from aureproof import __version__

app = typer.Typer(
    name="aureproof",
    help="Integrity layer for AI-agent evaluations.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"aureproof {__version__}")
        raise typer.Exit


@app.callback()
def main(
    _version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show the Aureproof version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Aureproof: every claim, backed by evidence."""


if __name__ == "__main__":  # pragma: no cover
    app()
