# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Durable, append-only, hash-chained journal on disk (issue #19).

Same entry format as a bundle's ``journal.jsonl`` (specs/bundle §5), so a run's
journal can be sealed as it is. Every append is flushed and fsynced before it
returns. On open, the chain is verified:

- a torn final line (a crash mid-write, so no trailing newline) is cut off,
  and an explicit ``journal_recovered`` event records the bytes dropped;
- any other damage (a bad hash, a broken link, an invalid entry) raises
  ``StorageError``: the run fails visibly instead of continuing on a bad record.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from aureproof.bundle.build import entry_hash
from aureproof.bundle.canonical import GENESIS, canonical_json
from aureproof.bundle.models import JournalEntry
from aureproof.contracts.events import Event, ObservationSource
from aureproof.contracts.strict_json import JsonInputError, loads_strict
from aureproof.storage.fs import StorageError


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._events: list[Event] = []
        self._head = GENESIS
        self.recovered_bytes = 0
        self._open()

    @property
    def events(self) -> list[Event]:
        return list(self._events)

    def _open(self) -> None:
        if self.path.is_symlink():
            raise StorageError(f"symlink rejected: {self.path}")
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.touch()
            return
        data = self.path.read_bytes()
        complete = data[: data.rfind(b"\n") + 1] if b"\n" in data else b""
        torn = len(data) - len(complete)
        for index, line in enumerate(complete.split(b"\n")[:-1]):
            try:
                entry = JournalEntry.model_validate(loads_strict(line, i_json=True))
                event = Event.model_validate(entry.event)
            except (JsonInputError, ValidationError) as exc:
                raise StorageError(f"journal line {index} is corrupt: {exc}") from exc
            if canonical_json(entry.model_dump(mode="json")) != line:
                raise StorageError(f"journal line {index} is not canonical")
            if entry.seq != index or entry.prev != self._head:
                raise StorageError(f"journal line {index} breaks the chain")
            if entry.hash != entry_hash(entry.seq, entry.prev, entry.event):
                raise StorageError(f"journal line {index} hash does not recompute")
            self._events.append(event)
            self._head = entry.hash
        if torn:
            with self.path.open("r+b") as fh:
                fh.truncate(len(complete))
                fh.flush()
                os.fsync(fh.fileno())
            self.recovered_bytes = torn
            self.append(
                episode_id="journal",
                kind="journal_recovered",
                payload={"note": f"dropped a torn final line of {torn} bytes on reopen"},
            )

    def append(
        self,
        *,
        episode_id: str,
        kind: str,
        payload: dict[str, Any] | None = None,
        attempt_id: str | None = None,
        blob_refs: list[str] | None = None,
    ) -> Event:
        event = Event(
            seq=len(self._events),
            episode_id=episode_id,
            attempt_id=attempt_id,
            actor="aureproof",
            kind=kind,
            observation_source=ObservationSource.CONTROLLER_OBSERVED,
            payload=payload,
            blob_refs=blob_refs or [],
        )
        body = event.model_dump(mode="json", exclude_none=True)
        current = entry_hash(event.seq, self._head, body)
        line = (
            canonical_json({"seq": event.seq, "prev": self._head, "event": body, "hash": current})
            + b"\n"
        )
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND)
        try:
            os.write(fd, line)
            os.fsync(fd)  # durable before we report success
        finally:
            os.close(fd)
        self._events.append(event)
        self._head = current
        return event

    def raw(self) -> bytes:
        return self.path.read_bytes()
