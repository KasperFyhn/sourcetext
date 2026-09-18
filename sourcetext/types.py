from __future__ import annotations

import datetime as dt
from typing import Any, ClassVar, Optional, TypeAlias, get_args

# The shape of a single value for each primary type — used both for the
# public-facing signatures (e.g. SourceText's predictions=/gold=) and, via
# get_args() below, as the one source of truth for each type's runtime
# validation, so the two can't silently drift apart.
IdValue: TypeAlias = str | int
TextValue: TypeAlias = str
LabelValue: TypeAlias = str | int | bool
ScoreValue: TypeAlias = float | int
GroupValue: TypeAlias = str | int
SpanValue: TypeAlias = list[dict[str, str | int]]
TemporalValue: TypeAlias = int | dt.date | dt.datetime
Point2DValue: TypeAlias = tuple[float | int, float | int]


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
        raise TypeError(f"{label} expects a column name (str) or an array-like of values, got {type(source).__name__}.")
    return list(source)


class _PrimaryType:
    """Base for all typed fields. Accepts a column name (resolved against `data=`)
    or a raw array of values directly, so the same type works in either input mode.
    """

    value_types: ClassVar[tuple[type, ...]] = ()
    definition_types: ClassVar[Optional[type]] = None

    def __init__(self, source: Any = None, *, definitions: Optional[Any] = None) -> None:
        if definitions is not None:
            if self.definition_types is None:
                raise TypeError(f"{type(self).__name__} does not accept definitions.")
            if not isinstance(definitions, self.definition_types):
                raise TypeError(
                    f"{type(self).__name__} expects its definitions to be of type "
                    f"{self.definition_types.__name__}, got {type(definitions).__name__}."
                )
        self.source = source
        self.definitions = definitions

    def resolve(self, data: Any = None) -> list:
        values = resolve_source(self.source, data, type(self).__name__)
        self._validate_values(values)
        return values

    def _validate_values(self, values: list) -> None:
        if not self.value_types:
            return
        for v in values:
            if v is None:
                continue
            if not isinstance(v, self.value_types):
                expected = ", ".join(t.__name__ for t in self.value_types)
                raise TypeError(
                    f"{type(self).__name__} expects values of type ({expected}), but got {type(v).__name__} ({v!r})."
                )

    def __repr__(self) -> str:
        secondary = f", secondary={self.definitions!r}" if self.definitions is not None else ""
        return f"{type(self).__name__}({self.source!r}{secondary})"


class IdType(_PrimaryType):
    """Categorical classification output: colored badge, filter dropdown."""

    value_types: ClassVar[tuple[type, ...]] = get_args(IdValue)


class FreeTextType(_PrimaryType):
    """User-supplied, read-only free-text metadata (e.g. an editorial note column).
    Not the interpretive-annotation field — that is owned by the served app itself.
    """

    value_types: ClassVar[tuple[type, ...]] = (str,)


class LabelType(_PrimaryType):
    """Categorical classification output: colored badge, filter dropdown."""

    value_types: ClassVar[tuple[type, ...]] = get_args(LabelValue)


class ScoreType(_PrimaryType):
    """Numerical score: range slider/filter, sortable."""

    value_types: ClassVar[tuple[type, ...]] = get_args(ScoreValue)


class GroupType(_PrimaryType):
    """Cluster/topic assignment; pairs with an optional GroupDefinition."""

    value_types: ClassVar[tuple[type, ...]] = get_args(GroupValue)
    definition_types: ClassVar[Optional[type]] = dict


class SpanType(_PrimaryType):
    """Per-instance list of spans: list[dict] with int start/end and str label
    (score optional). An instance may have zero, one, or many spans.
    """

    # Not derived via get_args() like the other types' value_types: a span's
    # shape is a nested list[dict], not a flat scalar union, so the per-span
    # structure still needs the custom checks in _validate_span below.
    value_types: ClassVar[tuple[type, ...]] = (list,)
    _REQUIRED_KEYS: ClassVar[set[str]] = {"start", "end", "label"}

    def _validate_values(self, values: list) -> None:
        super()._validate_values(values)
        for v in values:
            if v is None:
                continue
            for span in v:
                self._validate_span(span)

    @classmethod
    def _validate_span(cls, span: Any) -> None:
        if not isinstance(span, dict):
            raise TypeError(f"SpanType expects each span to be a dict, got {type(span).__name__} ({span!r}).")
        missing = cls._REQUIRED_KEYS - span.keys()
        if missing:
            raise TypeError(f"SpanType span {span!r} is missing required key(s): {sorted(missing)}.")
        start, end, label = span["start"], span["end"], span["label"]
        if not isinstance(start, int) or not isinstance(end, int):
            raise TypeError(f"SpanType span {span!r} must have integer 'start' and 'end' offsets.")
        if start < 0 or end < start:
            raise TypeError(f"SpanType span {span!r} has an invalid offset range (start={start}, end={end}).")
        if not isinstance(label, str):
            raise TypeError(f"SpanType span {span!r} must have a str 'label'.")


class TemporalType(_PrimaryType):
    """Orderable metadata for a sort axis / timeline. UI granularity dispatches on
    the underlying Python type: bare int -> year, date -> day, datetime -> timestamp.
    """

    value_types: ClassVar[tuple[type, ...]] = get_args(TemporalValue)

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
        if isinstance(value, dt.datetime):
            return "datetime"
        if isinstance(value, dt.date):
            return "day"
        return "year"


class Point2DType(_PrimaryType):
    """2D point per instance, e.g. a projected document embedding (UMAP/t-SNE
    output): (x, y) coordinates for a scatter-plot layout.
    """

    # Not derived via get_args() — same reason as SpanType: this is a
    # fixed-length pair, not a flat scalar union, so the per-point shape is
    # checked separately below.
    value_types: ClassVar[tuple[type, ...]] = (tuple, list)

    def _validate_values(self, values: list) -> None:
        super()._validate_values(values)
        for v in values:
            if v is None:
                continue
            if len(v) != 2 or not all(isinstance(coord, (int, float)) for coord in v):
                raise TypeError(f"Point2DType expects each point to be an (x, y) pair of numbers, got {v!r}.")
