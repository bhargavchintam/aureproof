# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Smoke tests: the package imports and the CLI reports its version."""

from __future__ import annotations

from typer.testing import CliRunner

from aureproof import __version__
from aureproof.cli.main import app

runner = CliRunner()


def test_package_exposes_version() -> None:
    assert isinstance(__version__, str)
    assert __version__


def test_cli_version_exits_zero_and_prints_name() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "aureproof" in result.stdout


def test_cli_help_lists_the_tagline() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Integrity layer" in result.output


def test_cli_no_args_is_help_not_crash() -> None:
    # `no_args_is_help=True` prints help and exits non-zero (usage), not a traceback.
    result = runner.invoke(app, [])
    assert result.exit_code in (0, 2)
    assert result.exception is None or isinstance(result.exception, SystemExit)
