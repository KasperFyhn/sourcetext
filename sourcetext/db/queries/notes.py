from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from sourcetext.db.schema import Document, Note


@dataclass
class NoteRow:
    document_id: str
    text: str
    updated_at: dt.datetime


def list_notes(session: Session) -> list[NoteRow]:
    """Every note, ordered by document id."""
    stmt = select(Note.document_id, Note.text, Note.updated_at).order_by(Note.document_id)
    return [NoteRow(*row) for row in session.execute(stmt)]


def get_note(session: Session, document_id: str) -> str:
    """The note on `document_id`, or "" if it has none. The document must exist."""
    if session.get(Document, document_id) is None:
        raise KeyError(f"No document with id {document_id!r}.")
    note = session.get(Note, document_id)
    return note.text if note is not None else ""
