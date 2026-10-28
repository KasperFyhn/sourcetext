from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from sourcetext.db.queries.fields import (
    IN_TABLES,
    RANGE_COERCERS,
    field_names,
    require_span_field,
    scalar_table_for_field,
)
from sourcetext.db.schema import Document, Span, Text


@dataclass
class FieldFilter:
    field: str
    op: Literal["in", "range", "span"]
    # Allowed values ("in"), or span labels ("span"; None stands for unlabelled).
    values: list[str | None] | None = None
    # Value bounds ("range"), or span score bounds ("span").
    min: float | str | None = None
    max: float | str | None = None
    # "span" only: a substring of the span text or norm text.
    text: str | None = None
    # "span" only: the exact type text (norm text, else span text) of the spans.
    type_text: str | None = None


@dataclass
class SearchFilter:
    """Documents where any of `fields` contains `text`, ignoring case. A field is a
    text field's name, or "text" for the source text."""

    text: str
    fields: list[str]
    op: Literal["search"] = "search"


Filter = FieldFilter | SearchFilter


def type_text():
    """SQL expression for the text a `Span` row is shown and grouped by: its norm
    text, or the text it covers if it has none. Spans sharing it and their label are
    one span type."""
    return func.coalesce(Span.norm_text, Span.span_text)


def span_conditions(f: FieldFilter, with_label: bool = True) -> list:
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
        conditions.append(type_text() == f.type_text)
    return conditions


def active_span_conditions(filters: list[Filter] | None, field_name: str, with_label: bool = True) -> list:
    """The conditions of every "span" filter on `field_name` in `filters`: the spans
    meeting them are the field's active spans, the only ones counted, shown or
    highlighted."""
    return [
        condition
        for f in filters or []
        if f.op == "span" and f.field == field_name
        for condition in span_conditions(f, with_label)
    ]


def _span_filter_subquery(session: Session, f: FieldFilter):
    """The ids of documents matching a "span" filter (see `apply_filters`)."""
    require_span_field(session, f.field)
    sub = select(Span.document_id).where(Span.field_name == f.field, *span_conditions(f))
    # Never correlated: the outer query may select from `spans` too (span stats).
    return sub.correlate(None).scalar_subquery()


def _search_subquery(session: Session, f: SearchFilter):
    """The ids of documents matching a search filter (see `SearchFilter`)."""
    if not f.text:
        raise ValueError("A 'search' filter requires non-empty `text`.")
    if not f.fields:
        raise ValueError("A 'search' filter requires non-empty `fields`.")
    text_fields = [name for name in f.fields if name != "text"]
    unknown = set(text_fields) - set(field_names(session, Text))
    if unknown:
        raise ValueError(f"Not text fields: {', '.join(map(repr, sorted(unknown)))}.")
    query = f.text.lower()
    conditions = []
    if "text" in f.fields:
        conditions.append(func.lower(Document.text).contains(query, autoescape=True))
    if text_fields:
        in_text_fields = select(Text.document_id).where(
            Text.field_name.in_(text_fields), func.lower(Text.value).contains(query, autoescape=True)
        )
        conditions.append(Document.id.in_(in_text_fields))
    condition = or_(*conditions)
    # Never correlated: the outer query may select from `documents` too.
    return select(Document.id).where(condition).correlate(None).scalar_subquery()


def apply_filters(session: Session, stmt, filters: list[Filter] | None, id_column=Document.id):
    """Narrow `stmt` (any select with `id_column`, by default `Document.id`, in its
    FROM clause) to documents
    matching every filter — AND across filters, OR within an "in" filter's
    `values`. A "span" filter matches documents with at least one span in the span
    field `field` meeting its conditions (see `span_conditions`). Each filter is
    applied as `<id_column> IN (<field's matching ids>)`, which composes safely
    regardless of `stmt`'s existing joins/columns (and doesn't duplicate documents
    with many matching spans). A search filter matches documents where any of its
    fields contains its text (see `SearchFilter`). Raises ValueError for an unknown field, an op that
    doesn't fit the field's type (e.g. "in" on a score field, or "span" on anything
    but a span field), or a bound that fails to coerce (e.g. a non-ISO date
    string)."""
    for f in filters or []:
        if isinstance(f, SearchFilter):
            stmt = stmt.where(id_column.in_(_search_subquery(session, f)))
            continue
        if f.op == "span":
            stmt = stmt.where(id_column.in_(_span_filter_subquery(session, f)))
            continue
        table = scalar_table_for_field(session, f.field)
        if table is None:
            raise ValueError(f"{f.field!r} is not a known field.")
        sub = select(table.document_id).where(table.field_name == f.field)
        if f.op == "in":
            if table not in IN_TABLES:
                raise ValueError(f"{f.field!r} does not support an 'in' filter.")
            if not f.values:
                raise ValueError("An 'in' filter requires a non-empty `values`.")
            sub = sub.where(table.value.in_(f.values))
        elif f.op == "range":
            coerce = RANGE_COERCERS.get(table)
            if coerce is None:
                raise ValueError(f"{f.field!r} does not support a 'range' filter.")
            if f.min is None and f.max is None:
                raise ValueError("A 'range' filter requires `min` and/or `max`.")
            if f.min is not None:
                sub = sub.where(table.value >= coerce(f.min))
            if f.max is not None:
                sub = sub.where(table.value <= coerce(f.max))
        else:
            raise ValueError(f"Unknown filter op {f.op!r}.")
        stmt = stmt.where(id_column.in_(sub.correlate(None).scalar_subquery()))
    return stmt
