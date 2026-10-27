"""Service-layer helpers for populating the tables defined in schema.py.

Each function takes a `Session` and adds rows to it, but does not commit —
callers control the transaction boundary, so a batch of documents and their
labels/scores/spans/... can be inserted together as one unit of work.

Typed fields are inserted in bulk (see `_insert_rows`) rather than as one ORM
object per row, which is far too slow for a corpus with ~1M spans; they return
how many rows they inserted.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Callable, Sequence

import pandas as pd
from sqlalchemy.orm import Session

from sourcetext.db.schema import (
    Document,
    Label,
    LabelDefinition,
    Note,
    Score,
    TemporalDate,
    TemporalDatetime,
    TemporalYear,
    Text,
)


def _insert_rows(session: Session, sql: str, columns: dict[str, list], **params: Any) -> int:
    """Run `sql`, an `INSERT ... SELECT ... FROM _rows`, with `columns` (equal-length
    lists) as the table `_rows`, on the session's DuckDB connection: in its current
    transaction, so it still commits or rolls back with the session. `params` bind
    `$name` placeholders. Returns the number of rows inserted.

    Columns are kept as object dtype, so a None stays NULL rather than becoming a
    NaN in a float column (which DuckDB would store as NaN). Rows keep their order
    (`rowid`), but `nextval` ids are only ordered across calls, not within one: DuckDB
    evaluates them in parallel. Ids therefore order fields by insertion, not rows."""
    n = len(next(iter(columns.values())))
    if n == 0:
        return 0
    rows = pd.DataFrame({name: pd.Series(values, dtype=object) for name, values in columns.items()})
    raw = session.connection().connection.driver_connection
    raw.register("_rows", rows)
    try:
        raw.execute(sql, params)
    finally:
        raw.unregister("_rows")
    return n


def add_documents(session: Session, ids: Sequence, texts: Sequence[str]) -> int:
    """Insert one `Document` row per `(id, text)` pair into `session`."""
    if len(ids) != len(texts):
        raise TypeError(f"`ids` has {len(ids)} value(s), but `texts` has {len(texts)}.")

    return _insert_rows(
        session,
        "INSERT INTO documents (id, text) SELECT id, text FROM _rows",
        {"id": [str(doc_id) for doc_id in ids], "text": list(texts)},
    )


def _add_scalar_field(
    session: Session,
    table: str,
    field_name: str,
    document_ids: Sequence,
    values: Sequence,
    cast: Callable[[Any], Any] | None = None,
) -> int:
    """Shared insert logic for the `(document_id, field_name, value)` tables:
    one row per `(document_id, value)` pair, skipping documents whose value is
    None (e.g. a partially-filled field)."""
    if len(document_ids) != len(values):
        raise TypeError(f"`document_ids` has {len(document_ids)} value(s), but `values` has {len(values)}.")

    pairs = [
        (str(doc_id), value if cast is None else cast(value))
        for doc_id, value in zip(document_ids, values)
        if value is not None
    ]
    return _insert_rows(
        session,
        f"INSERT INTO {table} (id, document_id, field_name, value) "
        f"SELECT nextval('{table}_id_seq'), document_id, $field_name, value FROM _rows",
        {"document_id": [doc_id for doc_id, _ in pairs], "value": [value for _, value in pairs]},
        field_name=field_name,
    )


def add_labels(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `Label` row per `(document_id, value)` pair under `field_name`."""
    return _add_scalar_field(session, Label.__tablename__, field_name, document_ids, values, cast=str)


def add_scores(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `Score` row per `(document_id, value)` pair under `field_name`."""
    return _add_scalar_field(session, Score.__tablename__, field_name, document_ids, values, cast=float)


def add_text(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `Text` row per `(document_id, value)` pair under `field_name`."""
    return _add_scalar_field(session, Text.__tablename__, field_name, document_ids, values)


def add_temporal_years(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `TemporalYear` row per `(document_id, value)` pair under `field_name`
    — for Temporal fields whose underlying Python value is a bare int."""
    return _add_scalar_field(session, TemporalYear.__tablename__, field_name, document_ids, values)


def add_temporal_dates(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `TemporalDate` row per `(document_id, value)` pair under `field_name`
    — for Temporal fields whose underlying Python value is a datetime.date."""
    return _add_scalar_field(session, TemporalDate.__tablename__, field_name, document_ids, values)


def add_temporal_datetimes(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `TemporalDatetime` row per `(document_id, value)` pair under `field_name`
    — for Temporal fields whose underlying Python value is a datetime.datetime."""
    return _add_scalar_field(session, TemporalDatetime.__tablename__, field_name, document_ids, values)


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
    if len(document_ids) != len(values):
        raise TypeError(f"`document_ids` has {len(document_ids)} value(s), but `values` has {len(values)}.")

    points = [(str(doc_id), point) for doc_id, point in zip(document_ids, values) if point is not None]
    return _insert_rows(
        session,
        "INSERT INTO points_2d (id, document_id, field_name, x, y) "
        "SELECT nextval('points_2d_id_seq'), document_id, $field_name, x, y FROM _rows",
        {
            "document_id": [doc_id for doc_id, _ in points],
            "x": [float(point[0]) for _, point in points],
            "y": [float(point[1]) for _, point in points],
        },
        field_name=field_name,
    )


def add_spans(session: Session, field_name: str, document_ids: Sequence, values: Sequence) -> int:
    """Insert one `Span` row per span dict under `field_name`. `values` is one
    list[dict] of spans per document (or None/[] for no spans) — a document
    with zero spans simply contributes no rows. Each span's `span_text`, the text it
    covers, is cut from its document's text here, once, rather than in every query
    (character offsets, 1-based in SQL), so the documents must be added first."""
    if len(document_ids) != len(values):
        raise TypeError(f"`document_ids` has {len(document_ids)} value(s), but `values` has {len(values)}.")

    spans = [(str(doc_id), span) for doc_id, doc_spans in zip(document_ids, values) for span in (doc_spans or [])]
    # A LEFT JOIN, so a span on a missing document still fails the foreign key
    # rather than silently being dropped.
    return _insert_rows(
        session,
        "INSERT INTO spans "
        "(span_id, document_id, field_name, span_start, span_end, span_text, label, score, norm_text) "
        "SELECT nextval('spans_span_id_seq'), r.document_id, $field_name, r.span_start, r.span_end, "
        "substring(d.text, r.span_start + 1, r.span_end - r.span_start), r.label, r.score, r.norm_text "
        "FROM _rows r LEFT JOIN documents d ON d.id = r.document_id",
        {
            "document_id": [doc_id for doc_id, _ in spans],
            "span_start": [span["start"] for _, span in spans],
            "span_end": [span["end"] for _, span in spans],
            "label": [span.get("label") for _, span in spans],
            "score": [span.get("score") for _, span in spans],
            "norm_text": [span.get("norm_text") for _, span in spans],
        },
        field_name=field_name,
    )


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
