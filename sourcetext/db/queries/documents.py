from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, literal_column, nulls_last, select
from sqlalchemy.orm import Session

from sourcetext.db.queries.fields import SCALAR_TABLES, list_span_fields, scalar_table_for_field, serialize_value
from sourcetext.db.queries.filters import Filter, active_span_conditions, apply_filters, type_text
from sourcetext.db.schema import Document, Note, Point2D, Span


@dataclass
class DocumentRow:
    id: str
    text: str
    values: dict[str, Any]
    note: str = ""


def count_documents(session: Session, filters: list[Filter] | None = None) -> int:
    stmt = apply_filters(session, select(func.count()).select_from(Document), filters)
    return session.execute(stmt).scalar_one()


def _populate_values_and_notes(
    session: Session, rows: dict[str, DocumentRow], filters: list[Filter] | None = None
) -> None:
    """Fill in field values and notes for an `{id: DocumentRow}` mapping, in place.
    A span field's value is its span types in the document (see `_span_types`),
    pruned by any "span" filter on that field in `filters`."""
    for _, table in SCALAR_TABLES:
        stmt = select(table.document_id, table.field_name, table.value).where(table.document_id.in_(rows.keys()))
        for document_id, field_name, value in session.execute(stmt):
            rows[document_id].values[field_name] = serialize_value(value)
    # Point2D isn't a `SCALAR_TABLES` entry: its value is an (x, y) pair, not a
    # single `.value` column, so it's serialized as a 2-element list instead.
    stmt = select(Point2D.document_id, Point2D.field_name, Point2D.x, Point2D.y).where(
        Point2D.document_id.in_(rows.keys())
    )
    for document_id, field_name, x, y in session.execute(stmt):
        rows[document_id].values[field_name] = [x, y]
    for field_name in list_span_fields(session):
        conditions = active_span_conditions(filters, field_name)
        for document_id, types in _span_types(session, field_name, rows.keys(), conditions).items():
            rows[document_id].values[field_name] = types
    stmt = select(Note.document_id, Note.text).where(Note.document_id.in_(rows.keys()))
    for document_id, text in session.execute(stmt):
        rows[document_id].note = text


def _span_types(session: Session, field_name: str, document_ids, conditions: list) -> dict[str, list[dict]]:
    """`{document_id: [{text, label, count}, ...]}`: each document's span types in
    `field_name` (spans meeting `conditions` only), most frequent first. Documents
    without such spans are left out."""
    text = type_text()
    count = func.count()
    stmt = (
        select(Span.document_id, text, Span.label, count)
        .where(Span.field_name == field_name, Span.document_id.in_(document_ids), *conditions)
        .group_by(Span.document_id, text, Span.label)
        .order_by(Span.document_id, count.desc(), text, nulls_last(Span.label))
    )
    out: dict[str, list[dict]] = {}
    for document_id, span_type_text, label, n in session.execute(stmt):
        out.setdefault(document_id, []).append({"text": span_type_text, "label": label, "count": n})
    return out


def list_documents(
    session: Session,
    limit: int = 50,
    offset: int = 0,
    sort_field: str | None = None,
    sort_desc: bool = False,
    filters: list[Filter] | None = None,
) -> list[DocumentRow]:
    """A page of documents with their scalar field values. In insertion order by
    default; pass `sort_field` (`"id"`, `"text"`, or any scalar field name) to
    order by that instead. Documents missing `sort_field`'s value sort last
    regardless of `sort_desc`. Raises ValueError if `sort_field` names neither
    `"id"`/`"text"` nor a known scalar field (e.g. a `point_2d` field, which has
    no single orderable value), or if `filters` is invalid (see `apply_filters`)."""
    if sort_field is None:
        stmt = select(Document).order_by(literal_column("rowid"))
    elif sort_field == "id":
        stmt = select(Document).order_by(Document.id.desc() if sort_desc else Document.id)
    elif sort_field == "text":
        stmt = select(Document).order_by(Document.text.desc() if sort_desc else Document.text)
    else:
        table = scalar_table_for_field(session, sort_field)
        if table is None:
            raise ValueError(f"{sort_field!r} is not a known sortable field.")
        values = select(table.document_id, table.value).where(table.field_name == sort_field).subquery()
        order_col = values.c.value.desc() if sort_desc else values.c.value
        stmt = (
            select(Document)
            .outerjoin(values, values.c.document_id == Document.id)
            .order_by(nulls_last(order_col), literal_column("rowid"))
        )
    stmt = apply_filters(session, stmt, filters)
    stmt = stmt.limit(limit).offset(offset)
    rows = {doc.id: DocumentRow(doc.id, doc.text, {}) for doc in session.execute(stmt).scalars()}
    _populate_values_and_notes(session, rows, filters)
    return list(rows.values())


def get_document(session: Session, document_id: str) -> DocumentRow | None:
    """A single document with its scalar field values and note, or None if it doesn't exist."""
    document = session.get(Document, document_id)
    if document is None:
        return None
    rows = {document.id: DocumentRow(document.id, document.text, {})}
    _populate_values_and_notes(session, rows)
    return rows[document.id]


def list_document_texts(session: Session) -> dict[str, str]:
    """`{document_id: text}` for every document."""
    return {document_id: text for document_id, text in session.execute(select(Document.id, Document.text))}
