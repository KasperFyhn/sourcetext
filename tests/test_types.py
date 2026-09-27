import datetime as dt

import numpy as np
import pandas as pd
import pytest

from sourcetext.types import (
    GroupType,
    LabelType,
    Point2DType,
    ScoreType,
    SpanType,
    TemporalType,
    TextType,
    to_python_value,
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
    assert g.definitions == {1: "topic one", 2: "topic two"}


def test_group_type_without_definitions_resolves_secondary_to_none():
    assert GroupType([1, 2]).definitions is None


def test_span_type_resolves_and_allows_empty_spans():
    spans = [[{"start": 0, "end": 3, "label": "ORG"}], []]
    assert SpanType(spans).resolve() == spans


def test_span_type_rejects_invalid_offsets():
    with pytest.raises(TypeError):
        SpanType([[{"start": 5, "end": 2, "label": "X"}]]).resolve()


def test_span_type_rejects_missing_keys():
    with pytest.raises(TypeError):
        SpanType([[{"start": 0, "end": 2}]]).resolve()


def test_span_type_rejects_non_list_value():
    with pytest.raises(TypeError):
        SpanType(["not-a-list"]).resolve()


def test_temporal_granularity_year():
    assert TemporalType([2020, 2021]).granularity() == "year"


def test_temporal_granularity_day():
    assert TemporalType([dt.date(2020, 1, 1)]).granularity() == "day"


def test_temporal_granularity_datetime():
    assert TemporalType([dt.datetime(2020, 1, 1, 12, 0)]).granularity() == "datetime"


def test_temporal_rejects_mixed_granularity():
    with pytest.raises(TypeError):
        TemporalType([2020, dt.date(2021, 1, 1)]).granularity()


def test_text_type_resolves():
    assert TextType(["a note"]).resolve() == ["a note"]


def test_group_type_definitions_can_be_rich_json_objects():
    definition = {"label": "Nature", "keywords": ["tree", "forest"]}
    g = GroupType([0], definitions={0: definition})
    assert g.definitions == {0: definition}


def test_point2d_type_resolves_tuples_and_lists():
    points = [(0.1, 0.2), [1, 2], None]
    assert Point2DType(points).resolve() == points


def test_point2d_type_rejects_wrong_length():
    with pytest.raises(TypeError):
        Point2DType([(0.1, 0.2, 0.3)]).resolve()


def test_point2d_type_rejects_non_numeric_coordinates():
    with pytest.raises(TypeError):
        Point2DType([("x", "y")]).resolve()


def test_point2d_type_rejects_non_sequence_value():
    with pytest.raises(TypeError):
        Point2DType(["not-a-point"]).resolve()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (np.int64(3), 3),
        (np.float32(0.5), 0.5),
        (np.bool_(True), True),
        (np.str_("a"), "a"),
        (np.datetime64("1850-01-01"), dt.date(1850, 1, 1)),
        (np.datetime64("1850-01-01T12:30:00.000000000"), dt.datetime(1850, 1, 1, 12, 30)),
        (pd.Timestamp("1850-01-01 12:30"), dt.datetime(1850, 1, 1, 12, 30)),
        (float("nan"), None),
        (np.float64("nan"), None),
        (np.datetime64("NaT", "ns"), None),
        (pd.NaT, None),
        (pd.NA, None),
        (np.array([1, 2]), [1, 2]),
        ((np.float32(1), np.float32(2)), (1.0, 2.0)),
        ({np.int64(0): {"w": [np.float32(0.5)]}}, {0: {"w": [0.5]}}),
    ],
)
def test_to_python_converts_to_plain_python(value, expected):
    result = to_python_value(value)
    assert result == expected
    assert type(result) is type(expected)


def test_to_python_leaves_plain_python_untouched():
    values = [1, 0.5, "a", True, dt.date(1850, 1, 1), None, [1, (2, 3)], {"k": "v"}]
    assert to_python_value(values) == values


def test_score_type_accepts_numpy_array():
    values = ScoreType(np.array([0.1, 0.2], dtype=np.float32)).resolve()
    assert all(type(v) is float for v in values)


def test_group_type_accepts_numpy_ints_and_definitions():
    field = GroupType(np.array([0, 1]), definitions={np.int64(0): "zero"})
    assert field.resolve() == [0, 1]
    assert field.definitions == {0: "zero"}


def test_point2d_type_accepts_2d_numpy_array():
    assert Point2DType(np.array([[0.5, 1.5], [2.0, 3.0]], dtype=np.float32)).resolve() == [[0.5, 1.5], [2.0, 3.0]]


def test_temporal_numpy_ints_are_years():
    assert TemporalType(np.array([1850, 1851])).granularity() == "year"


def test_temporal_nanosecond_datetime64_is_not_mistaken_for_years():
    values = np.array(["1850-01-01T12:00", "1851-01-01T12:00"], dtype="datetime64[ns]")
    assert TemporalType(values).granularity() == "datetime"


def test_span_type_accepts_numpy_offsets():
    spans = [[{"start": np.int64(0), "end": np.int64(3), "label": np.str_("X")}]]
    assert SpanType(spans).resolve() == [[{"start": 0, "end": 3, "label": "X"}]]


def test_label_type_treats_nan_from_dataframe_as_missing():
    df = pd.DataFrame({"label": ["a", None, "b"]})
    assert LabelType("label").resolve(df) == ["a", None, "b"]
