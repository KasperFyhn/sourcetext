from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sourcetext.db.queries.fields import category_value_subquery
from sourcetext.db.schema import Document


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
    rows = category_value_subquery(session, row_field)
    cols = category_value_subquery(session, col_field)
    stmt = (
        select(rows.c.value, cols.c.value, func.count())
        .select_from(Document)
        .outerjoin(rows, rows.c.document_id == Document.id)
        .outerjoin(cols, cols.c.document_id == Document.id)
        .where((rows.c.value.is_not(None)) | (cols.c.value.is_not(None)))
        .group_by(rows.c.value, cols.c.value)
    )
    return [CrosstabCell(row, col, count) for row, col, count in session.execute(stmt)]
