"""Persisting notes to a JSONL sidecar file.

Notes are the only data in sourcetext that the researcher creates rather than passes in
from Python, so they're the only thing persisted; every typed field is rebuilt from the
user's data on each run. The file holds one JSON record per note:

    {"document_id": "42", "text_hash": "3f2a…", "note": "…", "updated_at": "2026-…+00:00"}

Each record stores both the document's id and a hash of its text, so that notes can be
matched back to documents even when ids aren't stable: by id when the user passed
`ids=`, otherwise by text (see `NotesFile.load`).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import tempfile
import warnings
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from sqlalchemy.orm import Session

import sourcetext.db as db

DEFAULT_FILENAME = "sourcetext_notes.jsonl"

# Joins two different notes on the same document when merging, so neither is lost.
MERGE_SEPARATOR = "\n\n---\n\n"

MatchBy = Literal["id", "text"]

_REQUIRED_KEYS = ("document_id", "text_hash", "note", "updated_at")


def text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class LoadReport:
    path: Path
    # Documents that received a note from the file.
    loaded: int = 0
    # Documents with a different note both in this session and in the file; both were kept.
    merged: int = 0
    # Records matching no document in this corpus (kept in the file, but not shown).
    orphaned: int = 0
    # Matched by id, but the document's text differs from when the note was written.
    changed_text: int = 0
    # Matched by text, and attached to several documents sharing that text.
    duplicate_text: int = 0

    def messages(self) -> list[str]:
        """Human-readable notices for anything the user should know about."""
        messages = []
        if self.orphaned:
            messages.append(
                f"{self.orphaned} note(s) in {self.path} match no document in this corpus. "
                "They are kept in the file but not shown."
            )
        if self.changed_text:
            messages.append(
                f"{self.changed_text} note(s) in {self.path} belong to documents whose text "
                "has changed since the note was written."
            )
        if self.duplicate_text:
            messages.append(
                f"{self.duplicate_text} note(s) in {self.path} were attached to several documents "
                "that share the same text."
            )
        if self.merged:
            messages.append(
                f"{self.merged} document(s) had a different note both in this session and in "
                f"{self.path}. Both versions were kept, separated by {MERGE_SEPARATOR.strip()!r}."
            )
        return messages

    def warn(self) -> None:
        for message in self.messages():
            warnings.warn(message, stacklevel=3)


class NotesFile:
    """The notes file of one `SourceText`, or the lack of one (`path` is None).

    Notes live in the DB as usual; this mirrors them to `path` on every `save()`.
    Without a path, the app doesn't let notes be written at all, so a note is
    never kept only in memory.
    Records that match no document are held on to and written back untouched, so
    loading a subset of a corpus never destroys notes on the rest of it.
    """

    def __init__(self, path: str | os.PathLike | None = None, match_by: MatchBy = "text"):
        self.path = _resolve(path) if path is not None else None
        self.match_by = match_by
        self._orphans: list[dict[str, Any]] = []

    def load(self, session: Session) -> LoadReport:
        """Add the file's notes to the DB (without committing). A missing file is
        fine; it's created on the first save. Of several records competing for the
        same document, the most recent wins. A different note already in the DB is
        merged with it, older text first, so neither is lost."""
        report = LoadReport(self.path)
        if self.path is None or not self.path.exists():
            return report

        records = _read_records(self.path)
        texts = db.list_document_texts(session)
        orphans = []
        chosen: dict[str, dict[str, Any]] = {}
        if self.match_by == "id":
            for record in records:
                if record["document_id"] not in texts:
                    orphans.append(record)
                else:
                    _keep_latest(chosen, record["document_id"], record)
            report.changed_text = sum(
                record["text_hash"] != text_hash(texts[document_id]) for document_id, record in chosen.items()
            )
        else:
            ids_by_hash = defaultdict(list)
            for document_id, text in texts.items():
                ids_by_hash[text_hash(text)].append(document_id)
            by_hash: dict[str, dict[str, Any]] = {}
            for record in records:
                if record["text_hash"] not in ids_by_hash:
                    orphans.append(record)
                else:
                    _keep_latest(by_hash, record["text_hash"], record)
            for hash_, record in by_hash.items():
                document_ids = ids_by_hash[hash_]
                if len(document_ids) > 1:
                    report.duplicate_text += 1
                for document_id in document_ids:
                    chosen[document_id] = record

        existing = {note.document_id: note for note in db.list_notes(session)}
        for document_id, record in chosen.items():
            updated_at = _parse_timestamp(record["updated_at"])
            current = existing.get(document_id)
            if current is None:
                db.set_note(session, document_id, record["note"], updated_at)
                report.loaded += 1
            elif current.text != record["note"]:
                older, newer = (record["note"], current.text)
                if updated_at > current.updated_at:
                    older, newer = newer, older
                db.set_note(session, document_id, older + MERGE_SEPARATOR + newer)
                report.merged += 1

        report.orphaned = len(orphans)
        self._orphans = orphans
        return report

    def save(self, session: Session) -> None:
        """Write every note in the DB, plus the orphans, to the file. A no-op without
        a path. Written to a temporary file first, so a crash never leaves it half-written."""
        if self.path is None:
            return
        texts = db.list_document_texts(session)
        records = [
            {
                "document_id": note.document_id,
                "text_hash": text_hash(texts[note.document_id]),
                "note": note.text,
                "updated_at": _format_timestamp(note.updated_at),
            }
            for note in db.list_notes(session)
        ]
        records += self._orphans
        records.sort(key=lambda record: (record["document_id"], record["updated_at"]))

        fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            os.replace(tmp_path, self.path)
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    def set_path(self, path: str | os.PathLike, session: Session) -> LoadReport:
        """Start saving notes to `path` (without committing): load any notes already
        in it, then write the merged result. On failure, nothing changes."""
        previous = self.path, self._orphans
        self.path = _resolve(path)
        try:
            report = self.load(session)
            self.save(session)
        except BaseException:
            self.path, self._orphans = previous
            session.rollback()
            raise
        return report


def _resolve(path: str | os.PathLike) -> Path:
    return Path(path).expanduser().resolve()


def _keep_latest(chosen: dict[str, dict[str, Any]], key: str, record: dict[str, Any]) -> None:
    current = chosen.get(key)
    if current is None or _parse_timestamp(record["updated_at"]) >= _parse_timestamp(current["updated_at"]):
        chosen[key] = record


def _read_records(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("expected a JSON object")
                missing = [key for key in _REQUIRED_KEYS if key not in record]
                if missing:
                    raise ValueError(f"missing key(s) {', '.join(missing)}")
                if not all(isinstance(record[key], str) for key in _REQUIRED_KEYS):
                    raise ValueError(f"{', '.join(_REQUIRED_KEYS)} must be strings")
                _parse_timestamp(record["updated_at"])
            except ValueError as e:
                raise ValueError(f"Malformed notes file {path}, line {line_number}: {e}") from None
            records.append(record)
    return records


def _parse_timestamp(value: str) -> dt.datetime:
    """An ISO timestamp as naive UTC (naive input is taken to be UTC already)."""
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed


def _format_timestamp(value: dt.datetime) -> str:
    return value.replace(tzinfo=dt.timezone.utc).isoformat()
