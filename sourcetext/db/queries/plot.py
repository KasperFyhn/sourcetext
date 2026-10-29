from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import literal_column, select
from sqlalchemy.orm import Session

from sourcetext.db.queries.fields import category_value_subquery
from sourcetext.db.queries.filters import Filter, apply_filters
from sourcetext.db.schema import Document, Point2D, Score


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


def list_points_2d(
    session: Session,
    field_name: str,
    group_field: str | None = None,
    filters: list[Filter] | None = None,
) -> list[ScatterPointRow]:
    """All (x, y) points for one Point2DType field, joined to their document text
    and, if `group_field` is given, that label field's value per document.
    `filters` narrows which documents' points are included."""
    stmt = (
        select(Point2D.document_id, Point2D.x, Point2D.y, Document.text)
        .join(Document, Document.id == Point2D.document_id)
        .where(Point2D.field_name == field_name)
    )
    stmt = apply_filters(session, stmt, filters)
    if group_field is None:
        return [ScatterPointRow(doc_id, x, y, text) for doc_id, x, y, text in session.execute(stmt)]
    groups = category_value_subquery(session, group_field)
    stmt = stmt.add_columns(groups.c.value).outerjoin(groups, groups.c.document_id == Point2D.document_id)
    return [ScatterPointRow(doc_id, x, y, text, group) for doc_id, x, y, text, group in session.execute(stmt)]


def list_score_pairs(
    session: Session,
    x_field: str,
    y_field: str,
    group_field: str | None = None,
    filters: list[Filter] | None = None,
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
    stmt = apply_filters(session, stmt, filters)
    if group_field is None:
        return [ScatterPointRow(doc_id, x, y, text) for doc_id, x, y, text in session.execute(stmt)]
    groups = category_value_subquery(session, group_field)
    stmt = stmt.add_columns(groups.c.value).outerjoin(groups, groups.c.document_id == x_scores.c.document_id)
    return [ScatterPointRow(doc_id, x, y, text, group) for doc_id, x, y, text, group in session.execute(stmt)]


def list_strip_points(
    session: Session,
    x_field: str,
    row_field: str | None = None,
    color_field: str | None = None,
    filters: list[Filter] | None = None,
) -> list[StripPointRow]:
    """One point per document with a value for the ScoreType field `x_field`, and
    if given, its value for the label fields `row_field` (which row of the
    strip plot it lands in) and `color_field`. `filters` narrows which documents'
    points are included. Raises ValueError if `row_field` or `color_field` isn't a
    label field, or if `filters` is invalid (see `apply_filters`)."""
    stmt = (
        select(Score.document_id, Score.value, Document.text)
        .join(Document, Document.id == Score.document_id)
        .where(Score.field_name == x_field)
    )
    stmt = apply_filters(session, stmt, filters)
    for category_field in (row_field, color_field):
        if category_field is None:
            stmt = stmt.add_columns(literal_column("NULL"))
        else:
            values = category_value_subquery(session, category_field)
            stmt = stmt.add_columns(values.c.value).outerjoin(values, values.c.document_id == Score.document_id)
    return [StripPointRow(*row) for row in session.execute(stmt)]
