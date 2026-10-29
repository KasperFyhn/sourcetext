import pytest

from sourcetext.db.queries.fields import (
    FieldInfo,
    category_value_subquery,
    list_fields,
    list_plot_fields,
    list_span_fields,
    require_span_field,
    scalar_table_for_field,
)
from sourcetext.db.schema import Label, Score


def test_list_fields_includes_filter_metadata_per_field_type(session):
    assert list_fields(session) == [
        FieldInfo("prediction", "label", values=["neg", "pos"], definitions={"pos": "Positive", "neg": "Negative"}),
        FieldInfo("confidence", "score", min=0.4, max=0.9),
        FieldInfo("published", "temporal_date", min="2020-01-01", max="2022-01-01"),
        FieldInfo("comment", "text"),
        FieldInfo("embedding", "point_2d"),
        FieldInfo("entities", "span", values=["PER", None], min=0.5, max=0.9),
    ]


def test_list_plot_fields_lists_points_scores_and_labels(session):
    assert [(f.name, f.type) for f in list_plot_fields(session)] == [
        ("embedding", "point_2d"),
        ("confidence", "score"),
        ("prediction", "label"),
    ]


def test_scalar_table_for_field(session):
    assert scalar_table_for_field(session, "prediction") is Label
    assert scalar_table_for_field(session, "confidence") is Score
    assert scalar_table_for_field(session, "embedding") is None
    assert scalar_table_for_field(session, "nope") is None


def test_category_value_subquery_requires_a_label_field(session):
    category_value_subquery(session, "prediction")
    with pytest.raises(ValueError):
        category_value_subquery(session, "confidence")


def test_span_fields(session):
    assert list_span_fields(session) == ["entities"]
    require_span_field(session, "entities")
    with pytest.raises(ValueError):
        require_span_field(session, "prediction")
