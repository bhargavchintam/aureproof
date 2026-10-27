# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Read and write bundle directories safely (issue #16).

- Only regular files are read; any symlink (file or directory) is rejected,
  as are devices, sockets and FIFOs.
- Every path must be canonical (bundle spec §3); nothing can escape the root.
- Reading is bounded by ``MAX_BUNDLE_BYTES``.
- Writing is atomic: files go to a sibling temporary directory, which is then
  renamed into place. A crash never leaves a half-written bundle under the
  final name, and an existing directory is never overwritten.
"""

from __future__ import annotations

import os
import secrets
import shutil
import stat
from collections.abc import Mapping
from pathlib import Path

from aureproof.bundle.build import valid_path

MAX_BUNDLE_BYTES = 512 * 1024 * 1024


class StorageError(OSError):
    """The bundle directory cannot be read or written safely."""


def read_bundle(root: Path, *, max_bytes: int = MAX_BUNDLE_BYTES) -> dict[str, bytes]:
    if root.is_symlink():
        raise StorageError(f"{root} is a symlink")
    if not root.is_dir():
        raise StorageError(f"{root} is not a directory")
    files: dict[str, bytes] = {}
    total = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        here = Path(dirpath)
        for name in dirnames:
            if (here / name).is_symlink():
                raise StorageError(f"symlinked directory rejected: {here / name}")
        for name in filenames:
            path = here / name
            info = os.lstat(path)
            if stat.S_ISLNK(info.st_mode):
                raise StorageError(f"symlink rejected: {path}")
            if not stat.S_ISREG(info.st_mode):
                raise StorageError(f"not a regular file: {path}")
            rel = path.relative_to(root).as_posix()
            if not valid_path(rel):
                raise StorageError(f"non-canonical path: {rel!r}")
            total += info.st_size
            if total > max_bytes:
                raise StorageError(f"bundle larger than {max_bytes} bytes")
            with path.open("rb") as fh:
                files[rel] = fh.read()
    return files


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:  # pragma: no cover - platforms without directory fds
        return
    try:
        os.fsync(fd)
    except OSError:  # pragma: no cover
        pass
    finally:
        os.close(fd)


def write_bundle(files: Mapping[str, bytes], root: Path) -> None:
    if root.exists() or root.is_symlink():
        raise StorageError(f"{root} already exists; refusing to overwrite")
    for rel in files:
        if not valid_path(rel):
            raise StorageError(f"non-canonical path: {rel!r}")
    parent = root.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp = parent / f".{root.name}.tmp-{secrets.token_hex(8)}"
    tmp.mkdir()
    try:
        for rel, data in sorted(files.items()):
            target = tmp / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
        _fsync_dir(tmp)
        tmp.rename(root)  # atomic on one filesystem
        _fsync_dir(parent)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
