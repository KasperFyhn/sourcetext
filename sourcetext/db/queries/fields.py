from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, nulls_last, select
from sqlalchemy.orm import Session

from sourcetext.db.schema import (
    Label,
    LabelDefinition,
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
SCALAR_TABLES = [
    ("label", Label),
    ("score", Score),
    ("temporal_year", TemporalYear),
    ("temporal_date", TemporalDate),
    ("temporal_datetime", TemporalDatetime),
    ("text", Text),
]

# Tables whose values are a discrete set, suitable for an "in" (membership) filter.
IN_TABLES = (Label,)
# Tables whose values are orderable, suitable for a "range" (min/max) filter, along
# with how to coerce a raw filter bound (a JSON number or ISO string) to that column's
# Python type.
RANGE_COERCERS = {
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


def serialize_value(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def field_names(session: Session, table) -> list[str]:
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
    for table in IN_TABLES:
        in_values.update(_distinct_values(session, table))
    range_bounds: dict[str, tuple[Any, Any]] = {}
    for table in RANGE_COERCERS:
        range_bounds.update(_value_bounds(session, table))
    definitions = _label_definitions(session)

    fields = []
    for kind, table in SCALAR_TABLES:
        for name in field_names(session, table):
            if table in IN_TABLES:
                fields.append(FieldInfo(name, kind, values=in_values.get(name), definitions=definitions.get(name)))
            elif table in RANGE_COERCERS:
                lo, hi = range_bounds.get(name, (None, None))
                fields.append(FieldInfo(name, kind, min=serialize_value(lo), max=serialize_value(hi)))
            else:
                fields.append(FieldInfo(name, kind))
    fields += [FieldInfo(name, "point_2d") for name in field_names(session, Point2D)]
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
    fields = [FieldInfo(name, "point_2d") for name in field_names(session, Point2D)]
    fields += [FieldInfo(name, "score") for name in field_names(session, Score)]
    definitions = _label_definitions(session)
    fields += [FieldInfo(name, "label", definitions=definitions.get(name)) for name in field_names(session, Label)]
    return fields


def scalar_table_for_field(session: Session, field_name: str):
    """The `SCALAR_TABLES` table holding values for `field_name`, or None if it
    names no scalar field (unknown, or a non-scalar type like `point_2d`)."""
    for _, table in SCALAR_TABLES:
        exists = session.execute(select(table.id).where(table.field_name == field_name).limit(1)).first()
        if exists:
            return table
    return None


def category_value_subquery(session: Session, field_name: str):
    """A `(document_id, value)` subquery for one label field, for an
    optional outer join onto a plot query — documents without a value just get None
    rather than being dropped (unlike a missing axis value, a missing color or
    category shouldn't hide the point). Raises ValueError if `field_name` isn't a
    label field."""
    table = scalar_table_for_field(session, field_name)
    if table not in IN_TABLES:
        raise ValueError(f"{field_name!r} is not a label field.")
    return select(table.document_id, table.value).where(table.field_name == field_name).subquery()


def list_span_fields(session: Session) -> list[str]:
    """Every SpanType field name, in insertion order."""
    stmt = select(Span.field_name).group_by(Span.field_name).order_by(func.min(Span.span_id))
    return list(session.execute(stmt).scalars())


def require_span_field(session: Session, field_name: str) -> None:
    exists = session.execute(select(Span.span_id).where(Span.field_name == field_name).limit(1)).first()
    if not exists:
        raise ValueError(f"{field_name!r} is not a span field.")
