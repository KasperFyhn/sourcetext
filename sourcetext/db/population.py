"""Service-layer helpers for populating the tables defined in schema.py.

Each function takes a `Session` and adds rows to it, but does not commit —
callers control the transaction boundary, so a batch of documents and their
labels/scores/spans/... can be inserted together as one unit of work.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence, TypeVar

from sqlalchemy.orm import Session

from sourcetext.db.schema import (
    Document,
    FreeText,
    Group,
    GroupDefinition,
    Label,
    Note,
    Point2D,
    Score,
    Span,
    TemporalDate,
    TemporalDatetime,
    TemporalYear,
)

_ScalarModel = TypeVar("_ScalarModel", Label, Score, Group, TemporalYear, TemporalDate, TemporalDatetime, FreeText)


def add_documents(session: Session, ids: Sequence, texts: Sequence[str]) -> list[Document]:
    """Insert one `Document` row per `(id, text)` pair into `session`."""
    if len(ids) != len(texts):
        raise TypeError(f"`ids` has {len(ids)} value(s), but `texts` has {len(texts)}.")

    documents = [Document(id=str(doc_id), text=text) for doc_id, text in zip(ids, texts)]
    session.add_all(documents)
    return documents


def _add_scalar_field(
    session: Session,
    model: type[_ScalarModel],
    field_name: str,
    document_ids: Sequence,
    values: Sequence,
    cast: Callable[[Any], Any] | None = None,
) -> list[_ScalarModel]:
    """Shared insert logic for the `(document_id, field_name, value)` tables:
    one row per `(document_id, value)` pair, skipping documents whose value is
    None (e.g. a partially-filled field)."""
    if len(document_ids) != len(values):
        raise TypeError(f"`document_ids` has {len(document_ids)} value(s), but `values` has {len(values)}.")

    rows = [
        model(document_id=str(doc_id), field_name=field_name, value=value if cast is None else cast(value))
        for doc_id, value in zip(document_ids, values)
        if value is not None
    ]
    session.add_all(rows)
    return rows


def add_labels(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> list[Label]:
    """Insert one `Label` row per `(document_id, value)` pair under `field_name`."""
    return _add_scalar_field(session, Label, field_name, document_ids, values, cast=str)


def add_scores(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> list[Score]:
    """Insert one `Score` row per `(document_id, value)` pair under `field_name`."""
    return _add_scalar_field(session, Score, field_name, document_ids, values, cast=float)


def add_groups(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> list[Group]:
    """Insert one `Group` row per `(document_id, value)` pair under `field_name`.
    `value` is the group id, stored as text so it lines up with GroupDefinition.group_id."""
    return _add_scalar_field(session, Group, field_name, document_ids, values, cast=str)


def add_free_text(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> list[FreeText]:
    """Insert one `FreeText` row per `(document_id, value)` pair under `field_name`."""
    return _add_scalar_field(session, FreeText, field_name, document_ids, values)


def add_temporal_years(
    session: Session, field_name: str, document_ids: Sequence, values: Sequence
) -> list[TemporalYear]:
    """Insert one `TemporalYear` row per `(document_id, value)` pair under `field_name`
    — for Temporal fields whose underlying Python value is a bare int."""
    return _add_scalar_field(session, TemporalYear, field_name, document_ids, values)


def add_temporal_dates(
    session: Session, field_name: str, document_ids: Sequence, values: Sequence
) -> list[TemporalDate]:
    """Insert one `TemporalDate` row per `(document_id, value)` pair under `field_name`
    — for Temporal fields whose underlying Python value is a datetime.date."""
    return _add_scalar_field(session, TemporalDate, field_name, document_ids, values)


def add_temporal_datetimes(
    session: Session, field_name: str, document_ids: Sequence, values: Sequence
) -> list[TemporalDatetime]:
    """Insert one `TemporalDatetime` row per `(document_id, value)` pair under `field_name`
    — for Temporal fields whose underlying Python value is a datetime.datetime."""
    return _add_scalar_field(session, TemporalDatetime, field_name, document_ids, values)


def add_group_definitions(session: Session, field_name: str, definitions: dict) -> list[GroupDefinition]:
    """Insert one `GroupDefinition` row per `(group_id, definition)` pair, keyed by
    which GroupType field (`field_name`) they belong to."""
    rows = [
        GroupDefinition(field_name=field_name, group_id=str(group_id), definition=definition)
        for group_id, definition in definitions.items()
    ]
    session.add_all(rows)
    return rows


def add_points_2d(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> list[Point2D]:
    """Insert one `Point2D` row per `(document_id, (x, y))` pair under `field_name`."""
    if len(document_ids) != len(values):
        raise TypeError(f"`document_ids` has {len(document_ids)} value(s), but `values` has {len(values)}.")

    rows = [
        Point2D(document_id=str(doc_id), field_name=field_name, x=float(point[0]), y=float(point[1]))
        for doc_id, point in zip(document_ids, values)
        if point is not None
    ]
    session.add_all(rows)
    return rows


def add_spans(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> list[Span]:
    """Insert one `Span` row per span dict under `field_name`. `values` is one
    list[dict] of spans per document (or None/[] for no spans) — a document
    with zero spans simply contributes no rows."""
    if len(document_ids) != len(values):
        raise TypeError(f"`document_ids` has {len(document_ids)} value(s), but `values` has {len(values)}.")

    spans = [
        Span(
            document_id=str(doc_id),
            field_name=field_name,
            span_start=span["start"],
            span_end=span["end"],
            label=span["label"],
            score=span.get("score"),
        )
        for doc_id, doc_spans in zip(document_ids, values)
        for span in (doc_spans or [])
    ]
    session.add_all(spans)
    return spans


def set_note(session: Session, document_id: str, text: str) -> Note:
    """Create or replace the note for `document_id`. The document must exist."""
    if session.get(Document, str(document_id)) is None:
        raise KeyError(f"No document with id {document_id!r}.")
    return session.merge(Note(document_id=str(document_id), text=text))
