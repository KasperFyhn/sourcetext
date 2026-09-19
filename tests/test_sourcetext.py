import datetime as dt

import pandas as pd
import pytest

from sourcetext import FreeTextType, LabelType, Point2DType, SourceText, SpanType, TemporalType
from sourcetext.db.schema import (
    Document,
    FreeText,
    Group,
    GroupDefinition,
    Label,
    Point2D,
    Score,
    Span,
    TemporalDate,
    TemporalDatetime,
    TemporalYear,
)

TEXTS = ["The cat sat.", "A dog ran.", "Birds fly south."]


def test_list_mode_predictions_only():
    st = SourceText(TEXTS, predictions=["a", "b", "a"])
    docs = st._session.query(Document).order_by(Document.id).all()
    assert [d.text for d in docs] == TEXTS

    labels = st._session.query(Label).order_by(Label.id).all()
    assert [row.value for row in labels] == ["a", "b", "a"]
    assert {row.field_name for row in labels} == {"predictions"}


def test_predictions_gold_confidence_land_in_separate_tables():
    st = SourceText(
        TEXTS,
        predictions=["a", "b", "a"],
        predictions_confidence=[0.9, 0.4, 0.7],
        gold_labels=["a", "a", "a"],
    )
    field_names = {row.field_name for row in st._session.query(Label).all()}
    assert field_names == {"predictions", "gold_labels"}

    score_field_names = {s.field_name for s in st._session.query(Score).all()}
    assert score_field_names == {"predictions_confidence"}


def test_group_definitions_sugar_attaches_to_group_field():
    st = SourceText(TEXTS, groups=[0, 1, 0], group_definitions={0: "nature", 1: "animals"})

    groups = st._session.query(Group).order_by(Group.id).all()
    assert [g.value for g in groups] == ["0", "1", "0"]

    defs = {d.group_id: d.definition for d in st._session.query(GroupDefinition).all()}
    assert defs == {"0": "nature", "1": "animals"}


def test_group_definitions_can_be_rich_json_objects():
    definition = {"label": "Nature", "keywords": ["tree", "forest"], "scores": {"coherence": 0.8}}
    st = SourceText(TEXTS, groups=[0, 1, 0], group_definitions={0: definition})

    row = st._session.query(GroupDefinition).one()
    assert row.definition == definition


def test_group_definitions_without_groups_raises():
    with pytest.raises(TypeError):
        SourceText(TEXTS, group_definitions={0: "x"})


def test_dataframe_mode_resolves_columns_and_ids():
    df = pd.DataFrame(
        {
            "id": [10, 11, 12],
            "text": TEXTS,
            "prediction": ["a", "b", "a"],
            "year": [2020, 2021, 2022],
        }
    )
    st = SourceText(data=df, texts="text", predictions="prediction", ids="id", year=TemporalType("year"))
    assert st.doc_ids == [10, 11, 12]

    years = st._session.query(TemporalYear).order_by(TemporalYear.id).all()
    assert [y.value for y in years] == [2020, 2021, 2022]


def test_dataframe_mode_with_list_texts_raises():
    df = pd.DataFrame({"text": TEXTS})
    with pytest.raises(TypeError):
        SourceText(data=df, texts=TEXTS)


def test_list_mode_with_str_texts_raises():
    with pytest.raises(TypeError):
        SourceText(texts="text")


def test_missing_texts_raises():
    with pytest.raises(TypeError):
        SourceText()


def test_unrecognized_raw_field_requires_explicit_type():
    with pytest.raises(TypeError):
        SourceText(TEXTS, weird_field=[1, 2, 3])


def test_field_length_mismatch_raises():
    with pytest.raises(TypeError):
        SourceText(TEXTS, predictions=["a", "b"])


def test_secondary_label_does_not_collide_with_predictions():
    st = SourceText(TEXTS, predictions=["a", "a", "a"], secondary_label=LabelType(["x", "y", "z"]))
    field_names = {row.field_name for row in st._session.query(Label).all()}
    assert field_names == {"predictions", "secondary_label"}


def test_span_type_field():
    spans = [[{"start": 0, "end": 3, "label": "ANIMAL"}], [], [{"start": 0, "end": 5, "label": "ANIMAL"}]]
    st = SourceText(TEXTS, ner=SpanType(spans))
    rows = st._session.query(Span).order_by(Span.span_id).all()
    assert [r.document_id for r in rows] == ["0", "2"]


def test_free_text_field():
    st = SourceText(TEXTS, editorial_note=FreeTextType(["n1", "n2", "n3"]))
    rows = st._session.query(FreeText).order_by(FreeText.id).all()
    assert [r.value for r in rows] == ["n1", "n2", "n3"]


def test_ids_length_mismatch_raises():
    with pytest.raises(TypeError):
        SourceText(TEXTS, ids=[1, 2])


def test_temporal_date_and_datetime_granularities():
    st = SourceText(
        TEXTS,
        as_of=TemporalType([dt.date(2020, 1, 1), dt.date(2020, 1, 2), dt.date(2020, 1, 3)]),
        logged_at=TemporalType([dt.datetime(2020, 1, 1, 12, 0)] * 3),
    )
    dates = st._session.query(TemporalDate).order_by(TemporalDate.id).all()
    assert [d.value for d in dates] == [dt.date(2020, 1, 1), dt.date(2020, 1, 2), dt.date(2020, 1, 3)]

    datetimes = st._session.query(TemporalDatetime).all()
    assert all(d.value == dt.datetime(2020, 1, 1, 12, 0) for d in datetimes)


def test_point_2d_field():
    st = SourceText(TEXTS, embedding=Point2DType([(0.1, 0.2), [1, 2], None]))
    rows = st._session.query(Point2D).order_by(Point2D.id).all()
    assert [(r.document_id, r.x, r.y) for r in rows] == [("0", 0.1, 0.2), ("1", 1.0, 2.0)]
