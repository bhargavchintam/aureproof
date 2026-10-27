# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Provider-key handling for the live run (no Inspect import; tested in CI)."""

from __future__ import annotations

import hashlib
import stat
import zipfile
from pathlib import Path

KEY_VAR = "ANTHROPIC_API_KEY"


class KeyFileError(ValueError):
    pass


def load_key(env_file: Path, var: str = KEY_VAR) -> str:
    """Read ``var`` from a private (mode 600) env file without echoing it."""
    if not env_file.is_file():
        raise KeyFileError(f"missing {env_file}: add '{var}=...' and chmod 600")
    if stat.S_IMODE(env_file.stat().st_mode) & 0o077:
        raise KeyFileError(f"{env_file} is readable by others; run: chmod 600 {env_file}")
    for line in env_file.read_text().splitlines():
        name, sep, value = line.strip().removeprefix("export ").partition("=")
        if sep and name.strip() == var and value.strip().strip("'\""):
            return value.strip().strip("'\"")
    raise KeyFileError(f"{var} not found in {env_file}")


def leak_hits(log_path: str | Path, secret: str) -> list[str]:
    """Names of archive members that contain the secret verbatim."""
    needle = secret.encode()
    with zipfile.ZipFile(log_path) as archive:
        return [name for name in archive.namelist() if needle in archive.read(name)]


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
