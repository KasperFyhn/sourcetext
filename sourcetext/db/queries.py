from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, literal_column, nulls_last, select
from sqlalchemy.orm import Session

from sourcetext.db.schema import (
    Document,
    FreeText,
    Group,
    Label,
    Note,
    Point2D,
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


@dataclass
class ScatterPointRow:
    document_id: str
    x: float
    y: float
    text: str
    group: str | None = None


def _serialize(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _field_names(session: Session, table) -> list[str]:
    """Distinct field_name values for a `(id, field_name, ...)`-shaped table, in
    insertion order (first-seen id per name). Works for any table sharing that
    shape, whether via the `_ScalarField` mixin or a standalone model like `Point2D`."""
    stmt = select(table.field_name).group_by(table.field_name).order_by(func.min(table.id))
    return list(session.execute(stmt).scalars())


def list_fields(session: Session) -> list[FieldInfo]:
    """Every field name present in the DB, in insertion order within each type."""
    fields = []
    for kind, table in _SCALAR_TABLES:
        fields += [FieldInfo(name, kind) for name in _field_names(session, table)]
    fields += [FieldInfo(name, "point_2d") for name in _field_names(session, Point2D)]
    return fields


def list_scatter_fields(session: Session) -> list[FieldInfo]:
    """Every point_2d and score field name (the two types that fit on a scatterplot's
    axes), plus every group field name (for optionally coloring points by group)."""
    fields = [FieldInfo(name, "point_2d") for name in _field_names(session, Point2D)]
    fields += [FieldInfo(name, "score") for name in _field_names(session, Score)]
    fields += [FieldInfo(name, "group") for name in _field_names(session, Group)]
    return fields


def count_documents(session: Session) -> int:
    return session.execute(select(func.count()).select_from(Document)).scalar_one()


def _populate_values_and_notes(session: Session, rows: dict[str, DocumentRow]) -> None:
    """Fill in field values and notes for an `{id: DocumentRow}` mapping, in place."""
    for _, table in _SCALAR_TABLES:
        stmt = select(table.document_id, table.field_name, table.value).where(table.document_id.in_(rows.keys()))
        for document_id, field_name, value in session.execute(stmt):
            rows[document_id].values[field_name] = _serialize(value)
    # Point2D isn't a `_SCALAR_TABLES` entry: its value is an (x, y) pair, not a
    # single `.value` column, so it's serialized as a 2-element list instead.
    stmt = select(Point2D.document_id, Point2D.field_name, Point2D.x, Point2D.y).where(
        Point2D.document_id.in_(rows.keys())
    )
    for document_id, field_name, x, y in session.execute(stmt):
        rows[document_id].values[field_name] = [x, y]
    stmt = select(Note.document_id, Note.text).where(Note.document_id.in_(rows.keys()))
    for document_id, text in session.execute(stmt):
        rows[document_id].note = text


def _scalar_table_for_field(session: Session, field_name: str):
    """The `_SCALAR_TABLES` table holding values for `field_name`, or None if it
    names no scalar field (unknown, or a non-scalar type like `point_2d`)."""
    for _, table in _SCALAR_TABLES:
        exists = session.execute(select(table.id).where(table.field_name == field_name).limit(1)).first()
        if exists:
            return table
    return None


def list_documents(
    session: Session,
    limit: int = 50,
    offset: int = 0,
    sort_field: str | None = None,
    sort_desc: bool = False,
) -> list[DocumentRow]:
    """A page of documents with their scalar field values. In insertion order by
    default; pass `sort_field` (`"id"`, `"text"`, or any scalar field name) to
    order by that instead. Documents missing `sort_field`'s value sort last
    regardless of `sort_desc`. Raises ValueError if `sort_field` names neither
    `"id"`/`"text"` nor a known scalar field (e.g. a `point_2d` field, which has
    no single orderable value)."""
    if sort_field is None:
        stmt = select(Document).order_by(literal_column("rowid"))
    elif sort_field == "id":
        stmt = select(Document).order_by(Document.id.desc() if sort_desc else Document.id)
    elif sort_field == "text":
        stmt = select(Document).order_by(Document.text.desc() if sort_desc else Document.text)
    else:
        table = _scalar_table_for_field(session, sort_field)
        if table is None:
            raise ValueError(f"{sort_field!r} is not a known sortable field.")
        values = select(table.document_id, table.value).where(table.field_name == sort_field).subquery()
        order_col = values.c.value.desc() if sort_desc else values.c.value
        stmt = (
            select(Document)
            .outerjoin(values, values.c.document_id == Document.id)
            .order_by(nulls_last(order_col), literal_column("rowid"))
        )
    stmt = stmt.limit(limit).offset(offset)
    rows = {doc.id: DocumentRow(doc.id, doc.text, {}) for doc in session.execute(stmt).scalars()}
    _populate_values_and_notes(session, rows)
    return list(rows.values())


def get_document(session: Session, document_id: str) -> DocumentRow | None:
    """A single document with its scalar field values and note, or None if it doesn't exist."""
    document = session.get(Document, document_id)
    if document is None:
        return None
    rows = {document.id: DocumentRow(document.id, document.text, {})}
    _populate_values_and_notes(session, rows)
    return rows[document.id]


def _group_value_subquery(group_field: str):
    """A `(document_id, value)` subquery for one GroupType field, for an optional
    outer join onto a scatter query — documents without a value for it just get
    `group=None` rather than being dropped (unlike the x/y axis fields, a missing
    group shouldn't hide the point)."""
    return select(Group.document_id, Group.value).where(Group.field_name == group_field).subquery()


def list_points_2d(session: Session, field_name: str, group_field: str | None = None) -> list[ScatterPointRow]:
    """All (x, y) points for one Point2DType field, joined to their document text
    and, if `group_field` is given, that GroupType field's value per document."""
    stmt = (
        select(Point2D.document_id, Point2D.x, Point2D.y, Document.text)
        .join(Document, Document.id == Point2D.document_id)
        .where(Point2D.field_name == field_name)
    )
    if group_field is None:
        return [ScatterPointRow(doc_id, x, y, text) for doc_id, x, y, text in session.execute(stmt)]
    groups = _group_value_subquery(group_field)
    stmt = stmt.add_columns(groups.c.value).outerjoin(groups, groups.c.document_id == Point2D.document_id)
    return [ScatterPointRow(doc_id, x, y, text, group) for doc_id, x, y, text, group in session.execute(stmt)]


def list_score_pairs(
    session: Session, x_field: str, y_field: str, group_field: str | None = None
) -> list[ScatterPointRow]:
    """Two ScoreType fields combined into (x, y) pairs, and if `group_field` is
    given, that GroupType field's value per document. Inner join on the two score
    fields: documents missing either score are simply omitted."""
    x_scores = select(Score.document_id, Score.value.label("x")).where(Score.field_name == x_field).subquery()
    y_scores = select(Score.document_id, Score.value.label("y")).where(Score.field_name == y_field).subquery()
    stmt = (
        select(x_scores.c.document_id, x_scores.c.x, y_scores.c.y, Document.text)
        .join(y_scores, y_scores.c.document_id == x_scores.c.document_id)
        .join(Document, Document.id == x_scores.c.document_id)
    )
    if group_field is None:
        return [ScatterPointRow(doc_id, x, y, text) for doc_id, x, y, text in session.execute(stmt)]
    groups = _group_value_subquery(group_field)
    stmt = stmt.add_columns(groups.c.value).outerjoin(groups, groups.c.document_id == x_scores.c.document_id)
    return [ScatterPointRow(doc_id, x, y, text, group) for doc_id, x, y, text, group in session.execute(stmt)]
