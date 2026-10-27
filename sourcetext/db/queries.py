from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import and_, func, literal_column, nulls_last, or_, select
from sqlalchemy.orm import Session

from sourcetext.db.schema import (
    Document,
    Label,
    LabelDefinition,
    Note,
    Point2D,
    Score,
    Span,
    TemporalDate,
    TemporalDatetime,
    TemporalYear,
    Text,
)

# Tables holding one scalar value per (document, field); enough for a tabular overview.
# Temporal fields get one `kind` per underlying table (rather than a shared "temporal")
# since the granularity determines both their filter value type (int vs. date vs.
# datetime) and which picker widget the UI renders.
_SCALAR_TABLES = [
    ("label", Label),
    ("score", Score),
    ("temporal_year", TemporalYear),
    ("temporal_date", TemporalDate),
    ("temporal_datetime", TemporalDatetime),
    ("text", Text),
]

# Tables whose values are a discrete set, suitable for an "in" (membership) filter.
_IN_TABLES = (Label,)
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
    # Filter metadata: distinct values for label fields (an "in" filter's
    # candidates), or the min/max bound for score/temporal fields (a "range" filter's
    # domain). None for field types with no filter (point_2d) or that need neither
    # (text, which filters by substring instead).
    values: list[Any] | None = None
    min: Any | None = None
    max: Any | None = None
    # Label fields only: `{value: definition}` from the field's `definitions=`,
    # for the UI to show what each value means. None if the field has none.
    definitions: dict[str, Any] | None = None


@dataclass
class FieldFilter:
    # The field filtered on. For "contains" only: "text" is the document's source
    # text, and None searches the source text and every text field.
    field: str | None
    op: Literal["in", "range", "contains", "span"]
    # Allowed values ("in"), or span labels ("span"; None stands for unlabelled).
    values: list[str | None] | None = None
    # Value bounds ("range"), or span score bounds ("span").
    min: float | str | None = None
    max: float | str | None = None
    # Substring to search for ("contains"; "span": in span text or norm text).
    text: str | None = None
    # "span" only: the exact type text (norm text, else span text) of the spans.
    type_text: str | None = None


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


@dataclass
class StripPointRow:
    document_id: str
    x: float
    text: str
    row: str | None = None
    color: str | None = None


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


def _label_definitions(session: Session) -> dict[str, dict[str, Any]]:
    """`{field_name: {value: definition}}` for every label field with definitions."""
    out: dict[str, dict[str, Any]] = {}
    stmt = select(LabelDefinition.field_name, LabelDefinition.value, LabelDefinition.definition)
    for name, value, definition in session.execute(stmt):
        out.setdefault(name, {})[value] = definition
    return out


def list_fields(session: Session) -> list[FieldInfo]:
    """Every field name present in the DB, in insertion order within each type,
    decorated with filter metadata (see `FieldInfo`)."""
    in_values: dict[str, list[Any]] = {}
    for table in _IN_TABLES:
        in_values.update(_distinct_values(session, table))
    range_bounds: dict[str, tuple[Any, Any]] = {}
    for table in _RANGE_COERCERS:
        range_bounds.update(_value_bounds(session, table))
    definitions = _label_definitions(session)

    fields = []
    for kind, table in _SCALAR_TABLES:
        for name in _field_names(session, table):
            if table in _IN_TABLES:
                fields.append(FieldInfo(name, kind, values=in_values.get(name), definitions=definitions.get(name)))
            elif table in _RANGE_COERCERS:
                lo, hi = range_bounds.get(name, (None, None))
                fields.append(FieldInfo(name, kind, min=_serialize(lo), max=_serialize(hi)))
            else:
                fields.append(FieldInfo(name, kind))
    fields += [FieldInfo(name, "point_2d") for name in _field_names(session, Point2D)]
    fields += _span_field_infos(session)
    return fields


def _span_field_infos(session: Session) -> list[FieldInfo]:
    """A span field's filter metadata: its distinct labels (None for unlabelled
    spans, last) and the bounds of its scores."""
    labels: dict[str, list[str | None]] = {}
    stmt = select(Span.field_name, Span.label).distinct().order_by(Span.field_name, nulls_last(Span.label))
    for name, label in session.execute(stmt):
        labels.setdefault(name, []).append(label)
    stmt = select(Span.field_name, func.min(Span.score), func.max(Span.score)).group_by(Span.field_name)
    bounds = {name: (lo, hi) for name, lo, hi in session.execute(stmt)}
    return [
        FieldInfo(name, "span", values=labels.get(name), min=bounds[name][0], max=bounds[name][1])
        for name in list_span_fields(session)
    ]


def list_plot_fields(session: Session) -> list[FieldInfo]:
    """Every field name that fits the plot view: point_2d fields (a ready-made
    position), score fields (a numeric axis), and label fields (a categorical axis,
    which turns the plot into a strip plot, or the point color)."""
    fields = [FieldInfo(name, "point_2d") for name in _field_names(session, Point2D)]
    fields += [FieldInfo(name, "score") for name in _field_names(session, Score)]
    definitions = _label_definitions(session)
    fields += [FieldInfo(name, "label", definitions=definitions.get(name)) for name in _field_names(session, Label)]
    return fields


def count_documents(session: Session, filters: list[FieldFilter] | None = None) -> int:
    stmt = _apply_filters(session, select(func.count()).select_from(Document), filters)
    return session.execute(stmt).scalar_one()


def _populate_values_and_notes(
    session: Session, rows: dict[str, DocumentRow], filters: list[FieldFilter] | None = None
) -> None:
    """Fill in field values and notes for an `{id: DocumentRow}` mapping, in place.
    A span field's value is its span types in the document (see `_span_types`),
    pruned by any "span" filter on that field in `filters`."""
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
    for field_name in list_span_fields(session):
        conditions = _active_span_conditions(filters, field_name)
        for document_id, types in _span_types(session, field_name, rows.keys(), conditions).items():
            rows[document_id].values[field_name] = types
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


def _type_text():
    """SQL expression for the text a `Span` row is shown and grouped by: its norm
    text, or the text it covers if it has none. Spans sharing it and their label are
    one span type."""
    return func.coalesce(Span.norm_text, Span.span_text)


def list_span_fields(session: Session) -> list[str]:
    """Every SpanType field name, in insertion order."""
    stmt = select(Span.field_name).group_by(Span.field_name).order_by(func.min(Span.span_id))
    return list(session.execute(stmt).scalars())


def _require_span_field(session: Session, field_name: str) -> None:
    exists = session.execute(select(Span.span_id).where(Span.field_name == field_name).limit(1)).first()
    if not exists:
        raise ValueError(f"{field_name!r} is not a span field.")


def _span_conditions(f: FieldFilter, with_label: bool = True) -> list:
    """The conditions a span must meet to match the "span" filter `f` (beyond being
    in `f.field`): a label among `f.values` (None matching unlabelled spans), a score
    within `f.min`/`f.max` (spans without a score fail any bound), `f.text` in the
    span text or norm text (case-insensitive), and exactly `f.type_text` as type
    text. `with_label=False` leaves out the label condition."""
    conditions = []
    if with_label and f.values:
        labels = [v for v in f.values if v is not None]
        options = [Span.label.in_(labels)] if labels else []
        if None in f.values:
            options.append(Span.label.is_(None))
        conditions.append(or_(*options))
    if f.min is not None:
        conditions.append(Span.score >= float(f.min))
    if f.max is not None:
        conditions.append(Span.score <= float(f.max))
    if f.text:
        query = f.text.lower()
        conditions.append(
            or_(
                func.lower(Span.span_text).contains(query, autoescape=True),
                func.lower(Span.norm_text).contains(query, autoescape=True),
            )
        )
    if f.type_text is not None:
        conditions.append(_type_text() == f.type_text)
    return conditions


def _active_span_conditions(filters: list[FieldFilter] | None, field_name: str, with_label: bool = True) -> list:
    """The conditions of every "span" filter on `field_name` in `filters`: the spans
    meeting them are the field's active spans, the only ones counted, shown or
    highlighted."""
    return [
        condition
        for f in filters or []
        if f.op == "span" and f.field == field_name
        for condition in _span_conditions(f, with_label)
    ]


def _span_filter_subquery(session: Session, f: FieldFilter):
    """The ids of documents matching a "span" filter (see `_apply_filters`)."""
    _require_span_field(session, f.field)
    sub = select(Span.document_id).where(Span.field_name == f.field, *_span_conditions(f))
    # Never correlated: the outer query may select from `spans` too (span stats).
    return sub.correlate(None).scalar_subquery()


def _span_types(session: Session, field_name: str, document_ids, conditions: list) -> dict[str, list[dict]]:
    """`{document_id: [{text, label, count}, ...]}`: each document's span types in
    `field_name` (spans meeting `conditions` only), most frequent first. Documents
    without such spans are left out."""
    type_text = _type_text()
    count = func.count()
    stmt = (
        select(Span.document_id, type_text, Span.label, count)
        .where(Span.field_name == field_name, Span.document_id.in_(document_ids), *conditions)
        .group_by(Span.document_id, type_text, Span.label)
        .order_by(Span.document_id, count.desc(), type_text, nulls_last(Span.label))
    )
    out: dict[str, list[dict]] = {}
    for document_id, text, label, n in session.execute(stmt):
        out.setdefault(document_id, []).append({"text": text, "label": label, "count": n})
    return out


def _text_search_subquery(f: FieldFilter):
    """The ids of documents whose source text (`f.field == "text"`), or source text
    or any text field value (`f.field is None`), contains `f.text`, ignoring case."""
    if not f.text:
        raise ValueError("A 'contains' filter requires non-empty `text`.")
    query = f.text.lower()
    condition = func.lower(Document.text).contains(query, autoescape=True)
    if f.field is None:
        in_text_fields = select(Text.document_id).where(func.lower(Text.value).contains(query, autoescape=True))
        condition = or_(condition, Document.id.in_(in_text_fields))
    # Never correlated: the outer query may select from `documents` too.
    return select(Document.id).where(condition).correlate(None).scalar_subquery()


def _apply_filters(session: Session, stmt, filters: list[FieldFilter] | None, id_column=Document.id):
    """Narrow `stmt` (any select with `id_column`, by default `Document.id`, in its
    FROM clause) to documents
    matching every filter — AND across filters, OR within an "in" filter's
    `values`. A "span" filter matches documents with at least one span in the span
    field `field` meeting its conditions (see `_span_conditions`). Each filter is
    applied as `<id_column> IN (<field's matching ids>)`, which composes safely
    regardless of `stmt`'s existing joins/columns (and doesn't duplicate documents
    with many matching spans). A "contains" filter searches its text field, or the
    source text if `field` is "text", or both the source text and every text field
    if `field` is None (see `_text_search_subquery`). Raises ValueError for an unknown field, an op that
    doesn't fit the field's type (e.g. "in" on a score field, or "span" on anything
    but a span field), or a bound that fails to coerce (e.g. a non-ISO date
    string)."""
    for f in filters or []:
        if f.op == "contains" and f.field in (None, "text"):
            stmt = stmt.where(id_column.in_(_text_search_subquery(f)))
            continue
        if f.field is None:
            raise ValueError(f"A {f.op!r} filter requires a `field`.")
        if f.op == "span":
            stmt = stmt.where(id_column.in_(_span_filter_subquery(session, f)))
            continue
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
            if table is not Text:
                raise ValueError(f"{f.field!r} does not support a 'contains' filter.")
            if not f.text:
                raise ValueError("A 'contains' filter requires non-empty `text`.")
            sub = sub.where(func.lower(table.value).contains(f.text.lower(), autoescape=True))
        else:
            raise ValueError(f"Unknown filter op {f.op!r}.")
        stmt = stmt.where(id_column.in_(sub.correlate(None).scalar_subquery()))
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


def _category_value_subquery(session: Session, field_name: str):
    """A `(document_id, value)` subquery for one label field, for an
    optional outer join onto a plot query — documents without a value just get None
    rather than being dropped (unlike a missing axis value, a missing color or
    category shouldn't hide the point). Raises ValueError if `field_name` isn't a
    label field."""
    table = _scalar_table_for_field(session, field_name)
    if table not in _IN_TABLES:
        raise ValueError(f"{field_name!r} is not a label field.")
    return select(table.document_id, table.value).where(table.field_name == field_name).subquery()


def list_points_2d(
    session: Session,
    field_name: str,
    group_field: str | None = None,
    filters: list[FieldFilter] | None = None,
) -> list[ScatterPointRow]:
    """All (x, y) points for one Point2DType field, joined to their document text
    and, if `group_field` is given, that label field's value per document.
    `filters` narrows which documents' points are included."""
    stmt = (
        select(Point2D.document_id, Point2D.x, Point2D.y, Document.text)
        .join(Document, Document.id == Point2D.document_id)
        .where(Point2D.field_name == field_name)
    )
    stmt = _apply_filters(session, stmt, filters)
    if group_field is None:
        return [ScatterPointRow(doc_id, x, y, text) for doc_id, x, y, text in session.execute(stmt)]
    groups = _category_value_subquery(session, group_field)
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
    given, that label field's value per document. Inner join on the two score
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
    groups = _category_value_subquery(session, group_field)
    stmt = stmt.add_columns(groups.c.value).outerjoin(groups, groups.c.document_id == x_scores.c.document_id)
    return [ScatterPointRow(doc_id, x, y, text, group) for doc_id, x, y, text, group in session.execute(stmt)]


def list_strip_points(
    session: Session,
    x_field: str,
    row_field: str | None = None,
    color_field: str | None = None,
    filters: list[FieldFilter] | None = None,
) -> list[StripPointRow]:
    """One point per document with a value for the ScoreType field `x_field`, and
    if given, its value for the label fields `row_field` (which row of the
    strip plot it lands in) and `color_field`. `filters` narrows which documents'
    points are included. Raises ValueError if `row_field` or `color_field` isn't a
    label field, or if `filters` is invalid (see `_apply_filters`)."""
    stmt = (
        select(Score.document_id, Score.value, Document.text)
        .join(Document, Document.id == Score.document_id)
        .where(Score.field_name == x_field)
    )
    stmt = _apply_filters(session, stmt, filters)
    for category_field in (row_field, color_field):
        if category_field is None:
            stmt = stmt.add_columns(literal_column("NULL"))
        else:
            values = _category_value_subquery(session, category_field)
            stmt = stmt.add_columns(values.c.value).outerjoin(values, values.c.document_id == Score.document_id)
    return [StripPointRow(*row) for row in session.execute(stmt)]


@dataclass
class CrosstabCell:
    row: str | None
    col: str | None
    count: int


def crosstab(session: Session, row_field: str, col_field: str) -> list[CrosstabCell]:
    """Document counts per (row_field value, col_field value) pair, for two label
    fields (e.g. gold labels vs. predictions: a confusion matrix). Documents with a
    value for only one of the fields count under None for the other; those with
    neither are left out. Raises ValueError if either isn't a label field."""
    rows = _category_value_subquery(session, row_field)
    cols = _category_value_subquery(session, col_field)
    stmt = (
        select(rows.c.value, cols.c.value, func.count())
        .select_from(Document)
        .outerjoin(rows, rows.c.document_id == Document.id)
        .outerjoin(cols, cols.c.document_id == Document.id)
        .where((rows.c.value.is_not(None)) | (cols.c.value.is_not(None)))
        .group_by(rows.c.value, cols.c.value)
    )
    return [CrosstabCell(row, col, count) for row, col, count in session.execute(stmt)]


@dataclass
class NoteRow:
    document_id: str
    text: str
    updated_at: dt.datetime


def list_notes(session: Session) -> list[NoteRow]:
    """Every note, ordered by document id."""
    stmt = select(Note.document_id, Note.text, Note.updated_at).order_by(Note.document_id)
    return [NoteRow(*row) for row in session.execute(stmt)]


def list_document_texts(session: Session) -> dict[str, str]:
    """`{document_id: text}` for every document."""
    return {document_id: text for document_id, text in session.execute(select(Document.id, Document.text))}


def get_note(session: Session, document_id: str) -> str:
    """The note on `document_id`, or "" if it has none. The document must exist."""
    if session.get(Document, document_id) is None:
        raise KeyError(f"No document with id {document_id!r}.")
    note = session.get(Note, document_id)
    return note.text if note is not None else ""


@dataclass
class SpanLabelRow:
    label: str | None
    spans: int
    documents: int


@dataclass
class SpanTypeRow:
    text: str
    label: str | None
    spans: int
    documents: int
    # How many distinct span texts the spans cover (more than 1 when a norm text
    # brings several surface forms together).
    variants: int


@dataclass
class SpanSummary:
    labels: list[SpanLabelRow]
    # The most frequent span types, up to the requested limit.
    types: list[SpanTypeRow]
    # How many span types matched in all, before the limit.
    total_types: int


def summarize_spans(
    session: Session,
    field_name: str,
    limit: int = 100,
    filters: list[FieldFilter] | None = None,
) -> SpanSummary:
    """An overview of one span field, for finding documents by their spans: span
    and document counts per label, and per span type (type text and label), most
    frequent first. Only the field's active spans are counted (see
    `_active_span_conditions`), except that the label counts ignore a label
    condition, so they stay an overview to pick labels from. Filters on other fields
    narrow which documents' spans are counted. Raises ValueError if `field_name`
    isn't a span field, or `filters` is invalid."""
    _require_span_field(session, field_name)
    other_filters = [f for f in filters or [] if not (f.op == "span" and f.field == field_name)]
    base = select(Span).where(Span.field_name == field_name)
    base = _apply_filters(session, base, other_filters, id_column=Span.document_id)

    spans = base.where(*_active_span_conditions(filters, field_name, with_label=False)).subquery()
    n_docs = func.count(spans.c.document_id.distinct())
    stmt = (
        select(spans.c.label, func.count(), n_docs)
        .group_by(spans.c.label)
        .order_by(n_docs.desc(), nulls_last(spans.c.label))
    )
    labels = [SpanLabelRow(*row) for row in session.execute(stmt)]

    spans = (
        base.where(*_active_span_conditions(filters, field_name))
        .with_only_columns(
            _type_text().label("text"),
            Span.span_text.label("span_text"),
            Span.label.label("label"),
            Span.document_id.label("document_id"),
        )
        .subquery()
    )
    n_docs = func.count(spans.c.document_id.distinct())
    grouped = select(
        spans.c.text, spans.c.label, func.count(), n_docs, func.count(spans.c.span_text.distinct())
    ).group_by(spans.c.text, spans.c.label)
    total = session.execute(select(func.count()).select_from(grouped.subquery())).scalar_one()
    stmt = grouped.order_by(n_docs.desc(), func.count().desc(), spans.c.text, nulls_last(spans.c.label)).limit(limit)
    return SpanSummary(labels, [SpanTypeRow(*row) for row in session.execute(stmt)], total)


@dataclass
class SpanRow:
    field: str
    start: int
    end: int
    # The text the span covers.
    text: str
    norm_text: str | None
    label: str | None
    score: float | None


def list_document_spans(session: Session, document_id: str, filters: list[FieldFilter] | None = None) -> list[SpanRow]:
    """Every span on `document_id`, across all span fields, in text order. Any
    "span" filters in `filters` prune their field's spans to its active ones (see
    `_active_span_conditions`); other filters are ignored. The document must
    exist."""
    if session.get(Document, document_id) is None:
        raise KeyError(f"No document with id {document_id!r}.")
    stmt = (
        select(
            Span.field_name,
            Span.span_start,
            Span.span_end,
            Span.span_text,
            Span.norm_text,
            Span.label,
            Span.score,
        )
        .where(Span.document_id == document_id)
        .order_by(Span.span_start, Span.span_end, Span.span_id)
    )
    for field_name in {f.field for f in filters or [] if f.op == "span"}:
        conditions = _active_span_conditions(filters, field_name)
        if conditions:
            stmt = stmt.where(or_(Span.field_name != field_name, and_(*conditions)))
    return [SpanRow(*row) for row in session.execute(stmt)]
