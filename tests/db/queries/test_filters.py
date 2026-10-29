import pytest
from sqlalchemy import select

from sourcetext.db.queries.filters import FieldFilter, SearchFilter, active_span_conditions, apply_filters
from sourcetext.db.schema import Document, Span


def _ids(session, *filters) -> set[str]:
    stmt = apply_filters(session, select(Document.id), list(filters))
    return set(session.execute(stmt).scalars())


def test_no_filters_keep_every_document(session):
    assert _ids(session) == {"d0", "d1", "d2"}
    assert set(session.execute(apply_filters(session, select(Document.id), None)).scalars()) == {"d0", "d1", "d2"}


def test_in_filter_matches_any_of_its_values(session):
    assert _ids(session, FieldFilter("prediction", "in", values=["neg"])) == {"d1"}
    assert _ids(session, FieldFilter("prediction", "in", values=["neg", "pos"])) == {"d0", "d1", "d2"}


def test_range_filter_bounds_are_inclusive_and_skip_missing_values(session):
    assert _ids(session, FieldFilter("confidence", "range", min=0.4)) == {"d0", "d1"}
    assert _ids(session, FieldFilter("confidence", "range", max=0.4)) == {"d1"}


def test_range_filter_coerces_iso_dates(session):
    assert _ids(session, FieldFilter("published", "range", min="2021-01-01", max="2021-12-31")) == {"d1"}


def test_filters_combine_with_and(session):
    assert _ids(
        session, FieldFilter("prediction", "in", values=["pos"]), FieldFilter("confidence", "range", min=0.5)
    ) == {"d0"}


def test_span_filter_matches_documents_with_a_matching_span(session):
    assert _ids(session, FieldFilter("entities", "span", values=["PER"])) == {"d0"}
    assert _ids(session, FieldFilter("entities", "span", values=[None])) == {"d1"}
    assert _ids(session, FieldFilter("entities", "span", min=0.6)) == {"d0"}
    assert _ids(session, FieldFilter("entities", "span", text="MERKEL")) == {"d0", "d1"}
    assert _ids(session, FieldFilter("entities", "span", type_text="Barack Obama")) == {"d0"}


def test_search_filter_ignores_case_and_treats_wildcards_literally(session):
    assert _ids(session, SearchFilter("merkel", ["text"])) == {"d0", "d1"}
    assert _ids(session, SearchFilter("FINE", ["comment"])) == {"d0"}
    assert _ids(session, SearchFilter("%", ["text", "comment"])) == {"d2"}


@pytest.mark.parametrize(
    "f",
    [
        FieldFilter("nope", "in", values=["x"]),
        FieldFilter("confidence", "in", values=["x"]),
        FieldFilter("prediction", "range", min=1),
        FieldFilter("prediction", "in", values=[]),
        FieldFilter("confidence", "range"),
        FieldFilter("published", "range", min="not a date"),
        FieldFilter("prediction", "span", values=["PER"]),
        SearchFilter("x", ["prediction"]),
        SearchFilter("", ["text"]),
        SearchFilter("x", []),
    ],
)
def test_invalid_filters_raise_value_error(session, f):
    with pytest.raises(ValueError):
        _ids(session, f)


def test_active_span_conditions_only_use_span_filters_on_that_field(session):
    filters = [
        FieldFilter("entities", "span", values=["PER"], min=0.6),
        FieldFilter("other_spans", "span", values=["LOC"]),
        FieldFilter("prediction", "in", values=["pos"]),
    ]
    conditions = active_span_conditions(filters, "entities")
    spans = session.execute(select(Span.span_text).where(Span.field_name == "entities", *conditions)).scalars()
    assert list(spans) == ["Obama"]
    assert len(active_span_conditions(filters, "entities", with_label=False)) == len(conditions) - 1
    assert active_span_conditions(filters, "missing") == []
