from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Literal

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
# Temporal fields get one `kind` per underlying table (rather than a shared "temporal")
# since the granularity determines both their filter value type (int vs. date vs.
# datetime) and which picker widget the UI renders.
_SCALAR_TABLES = [
    ("label", Label),
    ("score", Score),
    ("group", Group),
    ("temporal_year", TemporalYear),
    ("temporal_date", TemporalDate),
    ("temporal_datetime", TemporalDatetime),
    ("free_text", FreeText),
]

# Tables whose values are a discrete set, suitable for an "in" (membership) filter.
_IN_TABLES = (Label, Group)
# Tables whose values are orderable, suitable for a "range" (min/max) filter, along
# with how to coerce a raw filter bound (a JSON number or ISO string) to that column's
# Python type.
_RANGE_COERCERS = {
    Score: float,
    TemporalYear: int,
    TemporalDate: dt.date.fromisoformat,
    TemporalDatetime: dt.datetime.fromisoformat,
}


@dataclass
class FieldInfo:
    name: str
    type: str
    # Filter metadata: distinct values for label/group fields (an "in" filter's
    # candidates), or the min/max bound for score/temporal fields (a "range" filter's
    # domain). None for field types with no filter (point_2d) or that need neither
    # (free_text, which filters by substring instead).
    values: list[Any] | None = None
    min: Any | None = None
    max: Any | None = None


@dataclass
class FieldFilter:
    field: str
    op: Literal["in", "range", "contains"]
    values: list[str] | None = None
    min: float | str | None = None
    max: float | str | None = None
    text: str | None = None


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


def _distinct_values(session: Session, table) -> dict[str, list[Any]]:
    """`{field_name: [distinct values, sorted]}` for one table, in a single query
    (rather than one query per field) to build "in"-filter candidates."""
    stmt = select(table.field_name, table.value).distinct().order_by(table.field_name, table.value)
    out: dict[str, list[Any]] = {}
    for name, value in session.execute(stmt):
        out.setdefault(name, []).append(value)
    return out


def _value_bounds(session: Session, table) -> dict[str, tuple[Any, Any]]:
    """`{field_name: (min, max)}` for one table, in a single query, to build
    "range"-filter domains."""
    stmt = select(table.field_name, func.min(table.value), func.max(table.value)).group_by(table.field_name)
    return {name: (lo, hi) for name, lo, hi in session.execute(stmt)}


def list_fields(session: Session) -> list[FieldInfo]:
    """Every field name present in the DB, in insertion order within each type,
    decorated with filter metadata (see `FieldInfo`)."""
    in_values: dict[str, list[Any]] = {}
    for table in _IN_TABLES:
        in_values.update(_distinct_values(session, table))
    range_bounds: dict[str, tuple[Any, Any]] = {}
    for table in _RANGE_COERCERS:
        range_bounds.update(_value_bounds(session, table))

    fields = []
    for kind, table in _SCALAR_TABLES:
        for name in _field_names(session, table):
            if table in _IN_TABLES:
                fields.append(FieldInfo(name, kind, values=in_values.get(name)))
            elif table in _RANGE_COERCERS:
                lo, hi = range_bounds.get(name, (None, None))
                fields.append(FieldInfo(name, kind, min=_serialize(lo), max=_serialize(hi)))
            else:
                fields.append(FieldInfo(name, kind))
    fields += [FieldInfo(name, "point_2d") for name in _field_names(session, Point2D)]
    return fields


def list_scatter_fields(session: Session) -> list[FieldInfo]:
    """Every point_2d and score field name (the two types that fit on a scatterplot's
    axes), plus every group field name (for optionally coloring points by group)."""
    fields = [FieldInfo(name, "point_2d") for name in _field_names(session, Point2D)]
    fields += [FieldInfo(name, "score") for name in _field_names(session, Score)]
    fields += [FieldInfo(name, "group") for name in _field_names(session, Group)]
    return fields


def count_documents(session: Session, filters: list[FieldFilter] | None = None) -> int:
    stmt = _apply_filters(session, select(func.count()).select_from(Document), filters)
    return session.execute(stmt).scalar_one()


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


def _apply_filters(session: Session, stmt, filters: list[FieldFilter] | None):
    """Narrow `stmt` (any select with `Document` in its FROM clause) to documents
    matching every filter — AND across filters, OR within an "in" filter's
    `values`. Each filter is applied as `Document.id IN (<field's matching ids>)`,
    which composes safely regardless of `stmt`'s existing joins/columns since a
    document has at most one row per (table, field_name). Raises ValueError for an
    unknown field, an op that doesn't fit the field's type (e.g. "in" on a score
    field), or a bound that fails to coerce (e.g. a non-ISO date string)."""
    for f in filters or []:
        table = _scalar_table_for_field(session, f.field)
        if table is None:
            raise ValueError(f"{f.field!r} is not a known field.")
        sub = select(table.document_id).where(table.field_name == f.field)
        if f.op == "in":
            if table not in _IN_TABLES:
                raise ValueError(f"{f.field!r} does not support an 'in' filter.")
            if not f.values:
                raise ValueError("An 'in' filter requires a non-empty `values`.")
            sub = sub.where(table.value.in_(f.values))
        elif f.op == "range":
            coerce = _RANGE_COERCERS.get(table)
            if coerce is None:
                raise ValueError(f"{f.field!r} does not support a 'range' filter.")
            if f.min is None and f.max is None:
                raise ValueError("A 'range' filter requires `min` and/or `max`.")
            if f.min is not None:
                sub = sub.where(table.value >= coerce(f.min))
            if f.max is not None:
                sub = sub.where(table.value <= coerce(f.max))
        elif f.op == "contains":
            if table is not FreeText:
                raise ValueError(f"{f.field!r} does not support a 'contains' filter.")
            if not f.text:
                raise ValueError("A 'contains' filter requires non-empty `text`.")
            sub = sub.where(func.lower(table.value).like(f"%{f.text.lower()}%"))
        else:
            raise ValueError(f"Unknown filter op {f.op!r}.")
        stmt = stmt.where(Document.id.in_(sub.scalar_subquery()))
    return stmt


def list_documents(
    session: Session,
    limit: int = 50,
    offset: int = 0,
    sort_field: str | None = None,
    sort_desc: bool = False,
    filters: list[FieldFilter] | None = None,
) -> list[DocumentRow]:
    """A page of documents with their scalar field values. In insertion order by
    default; pass `sort_field` (`"id"`, `"text"`, or any scalar field name) to
    order by that instead. Documents missing `sort_field`'s value sort last
    regardless of `sort_desc`. Raises ValueError if `sort_field` names neither
    `"id"`/`"text"` nor a known scalar field (e.g. a `point_2d` field, which has
    no single orderable value), or if `filters` is invalid (see `_apply_filters`)."""
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
    stmt = _apply_filters(session, stmt, filters)
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


def list_points_2d(
    session: Session,
    field_name: str,
    group_field: str | None = None,
    filters: list[FieldFilter] | None = None,
) -> list[ScatterPointRow]:
    """All (x, y) points for one Point2DType field, joined to their document text
    and, if `group_field` is given, that GroupType field's value per document.
    `filters` narrows which documents' points are included."""
    stmt = (
        select(Point2D.document_id, Point2D.x, Point2D.y, Document.text)
        .join(Document, Document.id == Point2D.document_id)
        .where(Point2D.field_name == field_name)
    )
    stmt = _apply_filters(session, stmt, filters)
    if group_field is None:
        return [ScatterPointRow(doc_id, x, y, text) for doc_id, x, y, text in session.execute(stmt)]
    groups = _group_value_subquery(group_field)
    stmt = stmt.add_columns(groups.c.value).outerjoin(groups, groups.c.document_id == Point2D.document_id)
    return [ScatterPointRow(doc_id, x, y, text, group) for doc_id, x, y, text, group in session.execute(stmt)]


def list_score_pairs(
    session: Session,
    x_field: str,
    y_field: str,
    group_field: str | None = None,
    filters: list[FieldFilter] | None = None,
) -> list[ScatterPointRow]:
    """Two ScoreType fields combined into (x, y) pairs, and if `group_field` is
    given, that GroupType field's value per document. Inner join on the two score
    fields: documents missing either score are simply omitted. `filters` narrows
    which documents' points are included."""
    x_scores = select(Score.document_id, Score.value.label("x")).where(Score.field_name == x_field).subquery()
    y_scores = select(Score.document_id, Score.value.label("y")).where(Score.field_name == y_field).subquery()
    stmt = (
        select(x_scores.c.document_id, x_scores.c.x, y_scores.c.y, Document.text)
        .join(y_scores, y_scores.c.document_id == x_scores.c.document_id)
        .join(Document, Document.id == x_scores.c.document_id)
    )
    stmt = _apply_filters(session, stmt, filters)
    if group_field is None:
        return [ScatterPointRow(doc_id, x, y, text) for doc_id, x, y, text in session.execute(stmt)]
    groups = _group_value_subquery(group_field)
    stmt = stmt.add_columns(groups.c.value).outerjoin(groups, groups.c.document_id == x_scores.c.document_id)
    return [ScatterPointRow(doc_id, x, y, text, group) for doc_id, x, y, text, group in session.execute(stmt)]
