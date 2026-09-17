import datetime as dt

import pytest

from sourcetext.types import (
    FreeTextType,
    GroupDefinition,
    GroupType,
    LabelType,
    ScoreType,
    SpanType,
    Temporal,
)


def test_label_type_resolves_raw_array():
    assert LabelType(["a", "b", "a"]).resolve() == ["a", "b", "a"]


def test_label_type_rejects_wrong_value_type():
    with pytest.raises(TypeError):
        LabelType([1, "a", 3.5]).resolve()


def test_label_type_column_name_without_data_raises():
    with pytest.raises(TypeError):
        LabelType("missing_col").resolve()


def test_score_type_resolves():
    assert ScoreType([0.1, 0.9]).resolve() == [0.1, 0.9]


def test_group_type_with_dict_definitions():
    g = GroupType([1, 2, 1], definitions={1: "topic one", 2: "topic two"})
    assert g.resolve() == [1, 2, 1]
    assert g.resolve_secondary() == {1: "topic one", 2: "topic two"}


def test_group_type_without_definitions_resolves_secondary_to_none():
    assert GroupType([1, 2]).resolve_secondary() is None


def test_group_definition_rejects_non_str_values():
    with pytest.raises(TypeError):
        GroupType([1, 2], definitions={1: 5}).resolve_secondary()


def test_only_group_type_accepts_a_secondary():
    with pytest.raises(TypeError):
        LabelType([1, 2], secondary=GroupDefinition({1: "x"}))


def test_span_type_resolves_and_allows_empty_spans():
    spans = [[{"start": 0, "end": 3, "label": "ORG"}], []]
    assert SpanType(spans).resolve() == spans


def test_span_type_rejects_invalid_offsets():
    with pytest.raises(TypeError):
        SpanType([[{"start": 5, "end": 2, "label": "X"}]]).resolve()


def test_span_type_rejects_missing_keys():
    with pytest.raises(TypeError):
        SpanType([[{"start": 0, "end": 2}]]).resolve()


def test_temporal_granularity_year():
    assert Temporal([2020, 2021]).granularity() == "year"


def test_temporal_granularity_day():
    assert Temporal([dt.date(2020, 1, 1)]).granularity() == "day"


def test_temporal_granularity_datetime():
    assert Temporal([dt.datetime(2020, 1, 1, 12, 0)]).granularity() == "datetime"


def test_temporal_rejects_mixed_granularity():
    with pytest.raises(TypeError):
        Temporal([2020, dt.date(2021, 1, 1)]).granularity()


def test_free_text_type_resolves():
    assert FreeTextType(["a note"]).resolve() == ["a note"]
