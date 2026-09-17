import pandas as pd
import pytest

from sourcetext import FreeTextType, GroupDefinition, LabelType, SourceText, SpanType, Temporal

TEXTS = ["The cat sat.", "A dog ran.", "Birds fly south."]


def test_list_mode_predictions_only():
    st = SourceText(TEXTS, predictions=["a", "b", "a"])
    assert st._tables["instances"]["text"].tolist() == TEXTS
    assert st._tables["labels"]["value"].tolist() == ["a", "b", "a"]
    assert (st._tables["labels"]["field_name"] == "predictions").all()


def test_predictions_gold_confidence_land_in_separate_tables():
    st = SourceText(TEXTS, predictions=["a", "b", "a"], confidence=[0.9, 0.4, 0.7], gold=["a", "a", "a"])
    field_names = set(st._tables["labels"]["field_name"])
    assert field_names == {"predictions", "gold"}
    assert st._tables["scores"]["field_name"].unique().tolist() == ["confidence"]


def test_group_defs_sugar_attaches_to_group_field():
    st = SourceText(TEXTS, group=[0, 1, 0], group_defs={0: "nature", 1: "animals"})
    assert st._tables["groups"]["value"].tolist() == [0, 1, 0]
    defs = dict(zip(st._tables["group_definitions"]["group_id"], st._tables["group_definitions"]["definition"]))
    assert defs == {0: "nature", 1: "animals"}


def test_group_defs_without_group_raises():
    with pytest.raises(TypeError):
        SourceText(TEXTS, group_defs={0: "x"})


def test_dataframe_mode_resolves_columns_and_ids():
    df = pd.DataFrame(
        {
            "id": [10, 11, 12],
            "text": TEXTS,
            "prediction": ["a", "b", "a"],
            "year": [2020, 2021, 2022],
        }
    )
    st = SourceText(data=df, texts="text", predictions="prediction", ids="id", year=Temporal("year"))
    assert st.instance_ids == [10, 11, 12]
    assert st._tables["temporal_year"]["value"].tolist() == [2020, 2021, 2022]


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
    field_names = set(st._tables["labels"]["field_name"])
    assert field_names == {"predictions", "secondary_label"}


def test_span_type_field():
    spans = [[{"start": 0, "end": 3, "label": "ANIMAL"}], [], [{"start": 0, "end": 5, "label": "ANIMAL"}]]
    st = SourceText(TEXTS, ner=SpanType(spans))
    assert len(st._tables["spans"]) == 2
    assert st._tables["spans"]["instance_id"].tolist() == [0, 2]


def test_free_text_field():
    st = SourceText(TEXTS, editorial_note=FreeTextType(["n1", "n2", "n3"]))
    assert st._tables["free_text"]["value"].tolist() == ["n1", "n2", "n3"]


def test_ids_length_mismatch_raises():
    with pytest.raises(TypeError):
        SourceText(TEXTS, ids=[1, 2])
