from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, func, nulls_last, or_, select
from sqlalchemy.orm import Session

from sourcetext.db.queries.fields import require_span_field
from sourcetext.db.queries.filters import Filter, active_span_conditions, apply_filters, type_text
from sourcetext.db.schema import Document, Span


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
    filters: list[Filter] | None = None,
) -> SpanSummary:
    """An overview of one span field, for finding documents by their spans: span
    and document counts per label, and per span type (type text and label), most
    frequent first. Only the field's active spans are counted (see
    `active_span_conditions`), except that the label counts ignore a label
    condition, so they stay an overview to pick labels from. Filters on other fields
    narrow which documents' spans are counted. Raises ValueError if `field_name`
    isn't a span field, or `filters` is invalid."""
    require_span_field(session, field_name)
    other_filters = [f for f in filters or [] if not (f.op == "span" and f.field == field_name)]
    base = select(Span).where(Span.field_name == field_name)
    base = apply_filters(session, base, other_filters, id_column=Span.document_id)

    spans = base.where(*active_span_conditions(filters, field_name, with_label=False)).subquery()
    n_docs = func.count(spans.c.document_id.distinct())
    stmt = (
        select(spans.c.label, func.count(), n_docs)
        .group_by(spans.c.label)
        .order_by(n_docs.desc(), nulls_last(spans.c.label))
    )
    labels = [SpanLabelRow(*row) for row in session.execute(stmt)]

    spans = (
        base.where(*active_span_conditions(filters, field_name))
        .with_only_columns(
            type_text().label("text"),
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


def list_document_spans(session: Session, document_id: str, filters: list[Filter] | None = None) -> list[SpanRow]:
    """Every span on `document_id`, across all span fields, in text order. Any
    "span" filters in `filters` prune their field's spans to its active ones (see
    `active_span_conditions`); other filters are ignored. The document must
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
        conditions = active_span_conditions(filters, field_name)
        if conditions:
            stmt = stmt.where(or_(Span.field_name != field_name, and_(*conditions)))
    return [SpanRow(*row) for row in session.execute(stmt)]
