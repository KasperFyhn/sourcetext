"""Service-layer helpers for populating the tables defined in schema.py.

Each function takes a `Session` and adds rows to it, but does not commit —
callers control the transaction boundary, so a batch of documents and their
labels/scores/spans/... can be inserted together as one unit of work.

Typed fields are inserted with SQLAlchemy's bulk INSERT (see `_bulk_insert`)
rather than as one ORM object per row, which is far too slow for a corpus with
~1M spans; they return how many rows they inserted.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Callable, Sequence

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from sourcetext.db.schema import (
    Base,
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


def _bulk_insert(session: Session, model: type[Base], rows: list[dict[str, Any]]) -> int:
    """Insert `rows` (one dict of column values each) into `model`'s table with one
    batched INSERT, in the session's transaction. Returns how many rows were inserted.
    Rows keep their order (`rowid`), but autoincrement ids are not guaranteed to
    follow it within one call, so don't order rows by id within one field."""
    if rows:
        session.execute(insert(model), rows)
    return len(rows)


def _check_lengths(document_ids: Sequence, values: Sequence) -> None:
    if len(document_ids) != len(values):
        raise TypeError(f"`document_ids` has {len(document_ids)} value(s), but `values` has {len(values)}.")


def add_documents(session: Session, ids: Sequence, texts: Sequence[str]) -> int:
    """Insert one `Document` row per `(id, text)` pair into `session`."""
    if len(ids) != len(texts):
        raise TypeError(f"`ids` has {len(ids)} value(s), but `texts` has {len(texts)}.")

    return _bulk_insert(session, Document, [{"id": str(doc_id), "text": text} for doc_id, text in zip(ids, texts)])


def _add_scalar_field(
    session: Session,
    model: type[Label | Score | TemporalYear | TemporalDate | TemporalDatetime | Text],
    field_name: str,
    document_ids: Sequence,
    values: Sequence,
    cast: Callable[[Any], Any] | None = None,
) -> int:
    """Shared insert logic for the `(document_id, field_name, value)` tables:
    one row per `(document_id, value)` pair, skipping documents whose value is
    None (e.g. a partially-filled field)."""
    _check_lengths(document_ids, values)

    rows = [
        {"document_id": str(doc_id), "field_name": field_name, "value": value if cast is None else cast(value)}
        for doc_id, value in zip(document_ids, values)
        if value is not None
    ]
    return _bulk_insert(session, model, rows)


def add_labels(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `Label` row per `(document_id, value)` pair under `field_name`."""
    return _add_scalar_field(session, Label, field_name, document_ids, values, cast=str)


def add_scores(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `Score` row per `(document_id, value)` pair under `field_name`."""
    return _add_scalar_field(session, Score, field_name, document_ids, values, cast=float)


def add_text(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `Text` row per `(document_id, value)` pair under `field_name`."""
    return _add_scalar_field(session, Text, field_name, document_ids, values)


def add_temporal_years(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `TemporalYear` row per `(document_id, value)` pair under `field_name`
    — for Temporal fields whose underlying Python value is a bare int."""
    return _add_scalar_field(session, TemporalYear, field_name, document_ids, values)


def add_temporal_dates(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `TemporalDate` row per `(document_id, value)` pair under `field_name`
    — for Temporal fields whose underlying Python value is a datetime.date."""
    return _add_scalar_field(session, TemporalDate, field_name, document_ids, values)


def add_temporal_datetimes(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `TemporalDatetime` row per `(document_id, value)` pair under `field_name`
    — for Temporal fields whose underlying Python value is a datetime.datetime."""
    return _add_scalar_field(session, TemporalDatetime, field_name, document_ids, values)


def add_label_definitions(session: Session, field_name: str, definitions: dict) -> list[LabelDefinition]:
    """Insert one `LabelDefinition` row per `(value, definition)` pair, keyed by
    which LabelType field (`field_name`) they belong to."""
    rows = [
        LabelDefinition(field_name=field_name, value=str(value), definition=definition)
        for value, definition in definitions.items()
    ]
    session.add_all(rows)
    return rows


def add_points_2d(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `Point2D` row per `(document_id, (x, y))` pair under `field_name`."""
    _check_lengths(document_ids, values)

    rows = [
        {"document_id": str(doc_id), "field_name": field_name, "x": float(point[0]), "y": float(point[1])}
        for doc_id, point in zip(document_ids, values)
        if point is not None
    ]
    return _bulk_insert(session, Point2D, rows)


def add_spans(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `Span` row per span dict under `field_name`. `values` is one
    list[dict] of spans per document (or None/[] for no spans) — a document
    with zero spans simply contributes no rows. Each span's `span_text`, the text it
    covers, is cut from its document's text here, once, rather than in every query,
    so the documents must be added first."""
    _check_lengths(document_ids, values)

    spans = [(str(doc_id), span) for doc_id, doc_spans in zip(document_ids, values) for span in (doc_spans or [])]
    span_doc_ids = {doc_id for doc_id, _ in spans}
    texts = dict(
        session.execute(select(Document.id, Document.text).where(Document.id.in_(span_doc_ids))).tuples().all()
    )
    missing = span_doc_ids - texts.keys()
    if missing:
        raise KeyError(f"Spans given for document(s) that don't exist: {sorted(missing)[:5]!r}.")

    rows = [
        {
            "document_id": doc_id,
            "field_name": field_name,
            "span_start": span["start"],
            "span_end": span["end"],
            "span_text": texts[doc_id][span["start"] : span["end"]],
            "label": span.get("label"),
            "score": span.get("score"),
            "norm_text": span.get("norm_text"),
        }
        for doc_id, span in spans
    ]
    return _bulk_insert(session, Span, rows)


def set_note(session: Session, document_id: str, text: str, updated_at: dt.datetime | None = None) -> Note | None:
    """Create or replace the note for `document_id`, or delete it if `text` is empty.
    The document must exist. `updated_at` (naive UTC) defaults to now."""
    if session.get(Document, str(document_id)) is None:
        raise KeyError(f"No document with id {document_id!r}.")
    if not text:
        existing = session.get(Note, str(document_id))
        if existing is not None:
            session.delete(existing)
        return None
    if updated_at is None:
        updated_at = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    return session.merge(Note(document_id=str(document_id), text=text, updated_at=updated_at))
