from __future__ import annotations

from typing import Any

import pandas as pd

from sourcetext.types import FreeTextType, GroupType, LabelType, ScoreType, SpanType, Temporal, _PrimaryType

_SCALAR_TABLE_COLUMNS = ["instance_id", "field_name", "value"]

_TABLE_COLUMNS: dict[str, list[str]] = {
    "instances": ["instance_id", "text"],
    "labels": _SCALAR_TABLE_COLUMNS,
    "scores": _SCALAR_TABLE_COLUMNS,
    "groups": _SCALAR_TABLE_COLUMNS,
    "group_definitions": ["field_name", "group_id", "definition"],
    "spans": ["span_id", "instance_id", "field_name", "span_start", "span_end", "label", "score"],
    "temporal_year": _SCALAR_TABLE_COLUMNS,
    "temporal_date": _SCALAR_TABLE_COLUMNS,
    "temporal_datetime": _SCALAR_TABLE_COLUMNS,
    "free_text": _SCALAR_TABLE_COLUMNS,
}


def empty_tables() -> dict[str, pd.DataFrame]:
    return {name: pd.DataFrame(columns=columns) for name, columns in _TABLE_COLUMNS.items()}


def add_field(
    tables: dict[str, pd.DataFrame],
    field_name: str,
    typed_field: _PrimaryType,
    instance_ids: list,
    data: Any,
) -> None:
    values = typed_field.resolve(data)
    if len(values) != len(instance_ids):
        raise TypeError(
            f"`{field_name}` has {len(values)} value(s), but there are "
            f"{len(instance_ids)} instances."
        )

    if isinstance(typed_field, SpanType):
        _add_spans(tables, field_name, instance_ids, values)
    elif isinstance(typed_field, LabelType):
        _add_scalar(tables, "labels", field_name, instance_ids, values)
    elif isinstance(typed_field, ScoreType):
        _add_scalar(tables, "scores", field_name, instance_ids, values)
    elif isinstance(typed_field, GroupType):
        _add_scalar(tables, "groups", field_name, instance_ids, values)
        definitions = typed_field.resolve_secondary(data)
        if definitions:
            _add_group_definitions(tables, field_name, definitions)
    elif isinstance(typed_field, Temporal):
        granularity = typed_field.granularity(data)
        _add_scalar(tables, f"temporal_{granularity}", field_name, instance_ids, values)
    elif isinstance(typed_field, FreeTextType):
        _add_scalar(tables, "free_text", field_name, instance_ids, values)
    else:
        raise TypeError(f"No internal-schema mapping registered for {type(typed_field).__name__}.")


def _add_scalar(
    tables: dict[str, pd.DataFrame], table: str, field_name: str, instance_ids: list, values: list
) -> None:
    rows = [
        {"instance_id": iid, "field_name": field_name, "value": v}
        for iid, v in zip(instance_ids, values)
        if v is not None
    ]
    if rows:
        tables[table] = pd.concat([tables[table], pd.DataFrame(rows)], ignore_index=True)


def _add_group_definitions(tables: dict[str, pd.DataFrame], field_name: str, definitions: dict) -> None:
    rows = [
        {"field_name": field_name, "group_id": group_id, "definition": definition}
        for group_id, definition in definitions.items()
    ]
    if rows:
        tables["group_definitions"] = pd.concat(
            [tables["group_definitions"], pd.DataFrame(rows)], ignore_index=True
        )


def _add_spans(tables: dict[str, pd.DataFrame], field_name: str, instance_ids: list, values: list) -> None:
    rows = []
    next_span_id = len(tables["spans"])
    for iid, spans in zip(instance_ids, values):
        for span in spans or []:
            rows.append(
                {
                    "span_id": next_span_id + len(rows),
                    "instance_id": iid,
                    "field_name": field_name,
                    "span_start": span["start"],
                    "span_end": span["end"],
                    "label": span["label"],
                    "score": span.get("score"),
                }
            )
    if rows:
        tables["spans"] = pd.concat([tables["spans"], pd.DataFrame(rows)], ignore_index=True)
