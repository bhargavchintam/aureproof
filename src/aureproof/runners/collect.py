# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Bounded collection of an agent-written artifact (issue #40).

``COLLECTOR`` is a small, auditable Python script that the runner executes
*inside the sandbox* (``python3 -c COLLECTOR <workspace> <name> <limit>``). It
never follows symlinks, accepts only a regular file whose real path stays in
the workspace, checks the size before reading, and reads at most ``limit + 1``
bytes, so a symlink to ``/dev/zero``, a FIFO, a directory or a huge file can
never cause an unbounded read. It prints one JSON line; ``interpret`` turns it
into a :class:`Capture` on the host. The limit is ``max_bytes`` of the matcher
version, so it is declared and versioned with the scoring semantics.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from aureproof.scoring import V0_1

ARTIFACT = "findings.json"
COLLECT_LIMIT = V0_1.max_bytes  # scoring.md §3; versioned by matcher_version

COLLECTOR = r"""
import base64, hashlib, json, os, stat, sys
root, name, limit = os.path.realpath(sys.argv[1]), sys.argv[2], int(sys.argv[3])
def out(**kw):
    sys.stdout.write(json.dumps(kw)); sys.exit(0)
if "/" in name or name in ("", ".", ".."):
    out(status="rejected", reason="bad_name")
path = os.path.join(root, name)
try:
    st = os.lstat(path)
except FileNotFoundError:
    out(status="absent")
if stat.S_ISLNK(st.st_mode):
    out(status="rejected", reason="symlink")
if not stat.S_ISREG(st.st_mode):
    out(status="rejected", reason="not_regular_file")
if os.path.dirname(os.path.realpath(path)) != root:
    out(status="rejected", reason="escapes_workspace")
if st.st_size > limit:
    out(status="rejected", reason="oversized", size=st.st_size)
fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
try:
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        out(status="rejected", reason="not_regular_file")
    chunks, total = [], 0
    while total <= limit:
        chunk = os.read(fd, min(65536, limit + 1 - total))
        if not chunk:
            break
        chunks.append(chunk); total += len(chunk)
finally:
    os.close(fd)
data = b"".join(chunks)
if len(data) > limit:
    out(status="rejected", reason="oversized", size=len(data))
out(status="captured", size=len(data), sha256=hashlib.sha256(data).hexdigest(),
    b64=base64.b64encode(data).decode("ascii"))
"""


@dataclass(frozen=True)
class Capture:
    status: Literal["captured", "absent", "rejected"]
    data: bytes | None = None
    sha256: str | None = None
    reason: str | None = None


def interpret(stdout: str, *, limit: int = COLLECT_LIMIT) -> Capture:
    """Host-side check of the collector's report. Distrusts it like any input."""
    if len(stdout) > 4 * limit:  # base64 of limit bytes is ~1.34x; anything bigger is hostile
        return Capture("rejected", reason="collector_output_too_large")
    try:
        report = json.loads(stdout)
        status = report["status"]
    except (ValueError, KeyError, TypeError):
        return Capture("rejected", reason="collector_output_unreadable")
    if status == "absent":
        return Capture("absent")
    if status != "captured":
        return Capture("rejected", reason=str(report.get("reason", "unknown")))
    try:
        data = base64.b64decode(report["b64"], validate=True)
    except (ValueError, KeyError, TypeError):
        return Capture("rejected", reason="collector_output_unreadable")
    digest = hashlib.sha256(data).hexdigest()
    if len(data) > limit or digest != report.get("sha256"):
        return Capture("rejected", reason="collector_output_inconsistent")
    return Capture("captured", data=data, sha256=digest)
