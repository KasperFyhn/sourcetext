from __future__ import annotations

from typing import Any

import pandas as pd

from sourcetext import schema
from sourcetext.types import GroupType, LabelType, ScoreType, _PrimaryType, resolve_source

_PRESET_TYPES: dict[str, type[_PrimaryType]] = {
    "predictions": LabelType,
    "gold": LabelType,
    "confidence": ScoreType,
    "group": GroupType,
}


class SourceText:
    def __init__(
        self,
        texts: list[str] | str | None = None,
        *,
        data: pd.DataFrame | None = None,
        ids: list | str | None = None,
        predictions: Any = None,
        gold: Any = None,
        **fields: Any,
    ) -> None:
        self._validate_mode(texts, data)
        text_values = resolve_source(texts, data, "texts")
        n = len(text_values)

        instance_ids = resolve_source(ids, data, "ids") if ids is not None else list(range(n))
        if len(instance_ids) != n:
            raise TypeError(f"`ids` has {len(instance_ids)} value(s), but `texts` has {n}.")

        typed_fields = self._collect_typed_fields(predictions=predictions, gold=gold, **fields)

        tables = schema.empty_tables()
        tables["instances"] = pd.DataFrame({"instance_id": instance_ids, "text": text_values})
        for field_name, typed_field in typed_fields.items():
            schema.add_field(tables, field_name, typed_field, instance_ids, data)

        self._tables = tables
        self.instance_ids = instance_ids

    @staticmethod
    def _validate_mode(texts: Any, data: pd.DataFrame | None) -> None:
        if texts is None:
            raise TypeError(
                "`texts` is required: a list of strings, or a column name (str) when `data=` is given."
            )
        if data is not None and not isinstance(texts, str):
            raise TypeError(
                "When `data=` is given, `texts` must be the name of the text column "
                f"(str), not a {type(texts).__name__}. Pass texts=\"<column name>\"."
            )
        if data is None and isinstance(texts, str):
            raise TypeError(
                "`texts` looks like a column name (str), but no `data=` DataFrame was "
                "given to resolve it against. Pass `data=<DataFrame>`, or give `texts` "
                "as a list of raw strings."
            )

    @staticmethod
    def _collect_typed_fields(predictions: Any = None, gold: Any = None, **fields: Any) -> dict[str, _PrimaryType]:
        named = {"predictions": predictions, "gold": gold, **fields}
        named = {k: v for k, v in named.items() if v is not None}
        group_defs = named.pop("group_defs", None)

        resolved: dict[str, _PrimaryType] = {}
        for field_name, value in named.items():
            if isinstance(value, _PrimaryType):
                resolved[field_name] = value
                continue
            preset_type = _PRESET_TYPES.get(field_name)
            if preset_type is None:
                raise TypeError(
                    f"`{field_name}` is not a recognized preset field "
                    f"({sorted(_PRESET_TYPES)}) and was not given as a typed field "
                    f"instance. Wrap arbitrary fields explicitly, "
                    f"e.g. {field_name}=LabelType(...)."
                )
            resolved[field_name] = preset_type(value)

        if group_defs is not None:
            if "group" not in resolved:
                raise TypeError("`group_defs` was given but no `group=` field was provided to attach it to.")
            group_field = resolved["group"]
            if not isinstance(group_field, GroupType):
                raise TypeError(
                    f"`group_defs` requires `group=` to be a GroupType, got {type(group_field).__name__}."
                )
            if group_field.secondary is not None:
                raise TypeError("`group` already has a `definitions=` secondary; don't also pass `group_defs=`.")
            resolved["group"] = GroupType(group_field.source, definitions=group_defs)

        return resolved
