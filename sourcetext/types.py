from __future__ import annotations

import datetime as _dt
from typing import Any, ClassVar, Optional


def resolve_source(source: Any, data: Any, label: str) -> list:
    if isinstance(source, str):
        if data is None:
            raise TypeError(
                f'{label}("{source}") looks like a column name, but no `data=` '
                "DataFrame was provided to resolve it against."
            )
        if source not in data.columns:
            raise TypeError(
                f'{label}("{source}") refers to a column not present in `data` '
                f"(available columns: {list(data.columns)})."
            )
        return list(data[source])
    if source is None:
        raise TypeError(f"{label} requires a column name or an array of values, got None.")
    if isinstance(source, dict) or not hasattr(source, "__iter__"):
        raise TypeError(
            f"{label} expects a column name (str) or an array-like of values, "
            f"got {type(source).__name__}."
        )
    return list(source)


class _SecondaryType:
    """Enriches a primary type's values with extra UI context (e.g. group definitions)."""

    def __init__(self, source: Any = None) -> None:
        self.source = source

    def resolve(self, data: Any = None) -> Any:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.source!r})"


class GroupDefinition(_SecondaryType):
    """dict[group_id, str] mapping group ids to a human-readable definition."""

    def resolve(self, data: Any = None) -> dict:
        value = self.source
        if not isinstance(value, dict):
            raise TypeError(
                f"GroupDefinition expects a dict[group_id, str], got {type(value).__name__}."
            )
        for key, val in value.items():
            if not isinstance(val, str):
                raise TypeError(
                    f"GroupDefinition values must be str; group {key!r} has value "
                    f"{val!r} ({type(val).__name__})."
                )
        return value


class _PrimaryType:
    """Base for all typed fields. Accepts a column name (resolved against `data=`)
    or a raw array of values directly, so the same type works in either input mode.
    """

    value_types: ClassVar[tuple[type, ...]] = ()
    secondary_type: ClassVar[Optional[type]] = None

    def __init__(self, source: Any = None, *, secondary: Optional[_SecondaryType] = None) -> None:
        if secondary is not None:
            if self.secondary_type is None:
                raise TypeError(f"{type(self).__name__} does not accept a secondary type.")
            if not isinstance(secondary, self.secondary_type):
                raise TypeError(
                    f"{type(self).__name__} expects its secondary field to be a "
                    f"{self.secondary_type.__name__}, got {type(secondary).__name__}."
                )
        self.source = source
        self.secondary = secondary

    def resolve(self, data: Any = None) -> list:
        values = resolve_source(self.source, data, type(self).__name__)
        self._validate_values(values)
        return values

    def resolve_secondary(self, data: Any = None) -> Any:
        return None if self.secondary is None else self.secondary.resolve(data)

    def _validate_values(self, values: list) -> None:
        if not self.value_types:
            return
        for v in values:
            if v is None:
                continue
            if not isinstance(v, self.value_types):
                expected = ", ".join(t.__name__ for t in self.value_types)
                raise TypeError(
                    f"{type(self).__name__} expects values of type ({expected}), "
                    f"but got {type(v).__name__} ({v!r})."
                )

    def __repr__(self) -> str:
        secondary = f", secondary={self.secondary!r}" if self.secondary is not None else ""
        return f"{type(self).__name__}({self.source!r}{secondary})"


class LabelType(_PrimaryType):
    """Categorical classification output: colored badge, filter dropdown."""

    value_types: ClassVar[tuple[type, ...]] = (str, int, bool)


class ScoreType(_PrimaryType):
    """Numerical score: range slider/filter, sortable."""

    value_types: ClassVar[tuple[type, ...]] = (float, int)


class GroupType(_PrimaryType):
    """Cluster/topic assignment; pairs with an optional GroupDefinition."""

    value_types: ClassVar[tuple[type, ...]] = (str, int)
    secondary_type: ClassVar[Optional[type]] = GroupDefinition

    def __init__(self, source: Any = None, *, definitions: GroupDefinition | dict | None = None) -> None:
        if isinstance(definitions, dict):
            definitions = GroupDefinition(definitions)
        super().__init__(source, secondary=definitions)


class SpanType(_PrimaryType):
    """Per-instance list of spans: list[dict] with int start/end and str label
    (score optional). An instance may have zero, one, or many spans.
    """

    _REQUIRED_KEYS: ClassVar[set[str]] = {"start", "end", "label"}

    def _validate_values(self, values: list) -> None:
        for v in values:
            if v is None:
                continue
            if not isinstance(v, list):
                raise TypeError(
                    f"SpanType expects a list[dict] of spans per instance, "
                    f"got {type(v).__name__} ({v!r})."
                )
            for span in v:
                self._validate_span(span)

    @classmethod
    def _validate_span(cls, span: Any) -> None:
        if not isinstance(span, dict):
            raise TypeError(
                f"SpanType expects each span to be a dict, got {type(span).__name__} ({span!r})."
            )
        missing = cls._REQUIRED_KEYS - span.keys()
        if missing:
            raise TypeError(f"SpanType span {span!r} is missing required key(s): {sorted(missing)}.")
        start, end, label = span["start"], span["end"], span["label"]
        if not isinstance(start, int) or not isinstance(end, int):
            raise TypeError(f"SpanType span {span!r} must have integer 'start' and 'end' offsets.")
        if start < 0 or end < start:
            raise TypeError(
                f"SpanType span {span!r} has an invalid offset range (start={start}, end={end})."
            )
        if not isinstance(label, str):
            raise TypeError(f"SpanType span {span!r} must have a str 'label'.")


class Temporal(_PrimaryType):
    """Orderable metadata for a sort axis / timeline. UI granularity dispatches on
    the underlying Python type: bare int -> year, date -> day, datetime -> timestamp.
    """

    value_types: ClassVar[tuple[type, ...]] = (int, _dt.date)

    def granularity(self, data: Any = None) -> str:
        values = [v for v in self.resolve(data) if v is not None]
        if not values:
            return "year"
        kinds = {self._granularity_of(v) for v in values}
        if len(kinds) > 1:
            raise TypeError(
                f"Temporal field mixes {sorted(kinds)} value types — all values must "
                "share one underlying Python type (int, datetime.date, or datetime.datetime)."
            )
        return kinds.pop()

    @staticmethod
    def _granularity_of(value: Any) -> str:
        if isinstance(value, _dt.datetime):
            return "datetime"
        if isinstance(value, _dt.date):
            return "day"
        return "year"


class FreeTextType(_PrimaryType):
    """User-supplied, read-only free-text metadata (e.g. an editorial note column).
    Not the interpretive-annotation field — that is owned by the served app itself.
    """

    value_types: ClassVar[tuple[type, ...]] = (str,)
