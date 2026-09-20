from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session

from sourcetext.db.schema import (
    Document,
    FreeText,
    Group,
    Label,
    Note,
    Score,
    TemporalDate,
    TemporalDatetime,
    TemporalYear,
)

# Tables holding one scalar value per (document, field); enough for a tabular overview.
_SCALAR_TABLES = [
    ("label", Label),
    ("score", Score),
    ("group", Group),
    ("temporal", TemporalYear),
    ("temporal", TemporalDate),
    ("temporal", TemporalDatetime),
    ("free_text", FreeText),
]


@dataclass
class FieldInfo:
    name: str
    type: str


@dataclass
class DocumentRow:
    id: str
    text: str
    values: dict[str, Any]
    note: str = ""


def _serialize(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def list_fields(session: Session) -> list[FieldInfo]:
    """Every scalar field name present in the DB, in insertion order within each type."""
    fields = []
    for kind, table in _SCALAR_TABLES:
        stmt = select(table.field_name).group_by(table.field_name).order_by(func.min(table.id))
        fields += [FieldInfo(name, kind) for name in session.execute(stmt).scalars()]
    return fields


def count_documents(session: Session) -> int:
    return session.execute(select(func.count()).select_from(Document)).scalar_one()


def list_documents(session: Session, limit: int = 50, offset: int = 0) -> list[DocumentRow]:
    """A page of documents (in insertion order) with their scalar field values."""
    stmt = select(Document).order_by(literal_column("rowid")).limit(limit).offset(offset)
    rows = {doc.id: DocumentRow(doc.id, doc.text, {}) for doc in session.execute(stmt).scalars()}
    for _, table in _SCALAR_TABLES:
        stmt = select(table.document_id, table.field_name, table.value).where(table.document_id.in_(rows.keys()))
        for document_id, field_name, value in session.execute(stmt):
            rows[document_id].values[field_name] = _serialize(value)
    stmt = select(Note.document_id, Note.text).where(Note.document_id.in_(rows.keys()))
    for document_id, text in session.execute(stmt):
        rows[document_id].note = text
    return list(rows.values())
