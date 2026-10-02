import datetime as dt
import json

from fastapi.testclient import TestClient

import sourcetext.db as db
from sourcetext.server.app import app


def _client(tmp_path) -> TestClient:
    # File-backed: TestClient runs the app in another thread, and in-memory DuckDB isn't shared across threads.
    create_session = db.get_sessionmaker(f"duckdb:///{tmp_path / 'test.duckdb'}")
    with create_session() as session:
        ids = [f"doc{i}" for i in range(3)]
        db.add_documents(session, ids, ["first", "second", "third"])
        db.add_labels(session, "predictions", ids, ["a", "b", "a"])
        db.add_scores(session, "confidence", ids, [0.1, 0.2, 0.3])
        db.add_scores(session, "readability", ids, [50.0, None, 70.0])
        db.add_points_2d(session, "embedding", ids, [(0.0, 0.0), (1.0, 1.0), None])
        db.add_groups(session, "topic", ids, ["weather", "politics", None])
        session.commit()
    app.state.db_sessionmaker = create_session
    # Not used as a context manager, so the lifespan (static build check) is skipped.
    return TestClient(app)


def _client_with_filter_fields(tmp_path) -> TestClient:
    """A separate dataset (not `_client`'s) adding text and all three temporal
    granularities, for filter tests that need them."""
    create_session = db.get_sessionmaker(f"duckdb:///{tmp_path / 'filters.duckdb'}")
    with create_session() as session:
        ids = [f"doc{i}" for i in range(3)]
        db.add_documents(session, ids, ["first", "second", "third"])
        db.add_text(session, "editor_note", ids, ["needs review", "looks good", "needs review too"])
        db.add_temporal_years(session, "pub_year", ids, [2020, 2021, 2022])
        db.add_temporal_dates(
            session, "pub_date", ids, [dt.date(2020, 1, 1), dt.date(2021, 6, 15), dt.date(2022, 12, 31)]
        )
        db.add_temporal_datetimes(
            session,
            "created_at",
            ids,
            [dt.datetime(2020, 1, 1, 10, 0), dt.datetime(2021, 6, 15, 12, 30), dt.datetime(2022, 12, 31, 23, 59)],
        )
        session.commit()
    app.state.db_sessionmaker = create_session
    return TestClient(app)


def test_tabular_route_returns_fields_and_values(tmp_path):
    body = _client(tmp_path).get("/api/documents/tabular").json()

    assert body["total"] == 3
    assert body["fields"] == [
        {"name": "predictions", "type": "label", "values": ["a", "b"], "min": None, "max": None},
        {"name": "confidence", "type": "score", "values": None, "min": 0.1, "max": 0.3},
        {"name": "readability", "type": "score", "values": None, "min": 50.0, "max": 70.0},
        {"name": "topic", "type": "group", "values": ["politics", "weather"], "min": None, "max": None},
        {"name": "embedding", "type": "point_2d", "values": None, "min": None, "max": None},
    ]
    assert [d["id"] for d in body["documents"]] == ["doc0", "doc1", "doc2"]
    assert body["documents"][1] == {
        "id": "doc1",
        "text": "second",
        "values": {"predictions": "b", "confidence": 0.2, "topic": "politics", "embedding": [1.0, 1.0]},
        "note": "",
    }


def test_tabular_route_paginates(tmp_path):
    body = _client(tmp_path).get("/api/documents/tabular", params={"limit": 2, "offset": 2}).json()

    assert body["total"] == 3
    assert [d["id"] for d in body["documents"]] == ["doc2"]


def test_tabular_route_sorts_by_id_desc(tmp_path):
    body = _client(tmp_path).get("/api/documents/tabular", params={"sortField": "id", "sortDir": "desc"}).json()

    assert [d["id"] for d in body["documents"]] == ["doc2", "doc1", "doc0"]


def test_tabular_route_sorts_by_score_field(tmp_path):
    body = _client(tmp_path).get("/api/documents/tabular", params={"sortField": "confidence", "sortDir": "desc"}).json()

    assert [d["id"] for d in body["documents"]] == ["doc2", "doc1", "doc0"]


def test_tabular_route_sort_puts_missing_values_last(tmp_path):
    # doc1's "readability" is None regardless of ascending or descending sort direction.
    client = _client(tmp_path)

    body = client.get("/api/documents/tabular", params={"sortField": "readability"}).json()
    assert [d["id"] for d in body["documents"]] == ["doc0", "doc2", "doc1"]

    body = client.get("/api/documents/tabular", params={"sortField": "readability", "sortDir": "desc"}).json()
    assert [d["id"] for d in body["documents"]] == ["doc2", "doc0", "doc1"]


def test_tabular_route_rejects_unsortable_field(tmp_path):
    response = _client(tmp_path).get("/api/documents/tabular", params={"sortField": "embedding"})
    assert response.status_code == 400


def test_tabular_route_rejects_unknown_sort_field(tmp_path):
    response = _client(tmp_path).get("/api/documents/tabular", params={"sortField": "nope"})
    assert response.status_code == 400


def test_tabular_route_filters_by_label_in(tmp_path):
    body = (
        _client(tmp_path)
        .get(
            "/api/documents/tabular",
            params={"filters": json.dumps([{"field": "predictions", "op": "in", "values": ["a"]}])},
        )
        .json()
    )

    assert {d["id"] for d in body["documents"]} == {"doc0", "doc2"}
    assert body["total"] == 2


def test_tabular_route_filters_by_score_range(tmp_path):
    body = (
        _client(tmp_path)
        .get(
            "/api/documents/tabular",
            params={"filters": json.dumps([{"field": "confidence", "op": "range", "min": 0.2}])},
        )
        .json()
    )

    assert {d["id"] for d in body["documents"]} == {"doc1", "doc2"}


def test_tabular_route_filters_by_text_contains(tmp_path):
    body = (
        _client_with_filter_fields(tmp_path)
        .get(
            "/api/documents/tabular",
            params={"filters": json.dumps([{"field": "editor_note", "op": "contains", "text": "needs"}])},
        )
        .json()
    )

    assert {d["id"] for d in body["documents"]} == {"doc0", "doc2"}


def test_tabular_route_filters_by_temporal_year_range(tmp_path):
    body = (
        _client_with_filter_fields(tmp_path)
        .get(
            "/api/documents/tabular",
            params={"filters": json.dumps([{"field": "pub_year", "op": "range", "min": 2021}])},
        )
        .json()
    )

    assert {d["id"] for d in body["documents"]} == {"doc1", "doc2"}


def test_tabular_route_filters_by_temporal_date_range(tmp_path):
    body = (
        _client_with_filter_fields(tmp_path)
        .get(
            "/api/documents/tabular",
            params={"filters": json.dumps([{"field": "pub_date", "op": "range", "max": "2021-12-31"}])},
        )
        .json()
    )

    assert {d["id"] for d in body["documents"]} == {"doc0", "doc1"}


def test_tabular_route_filters_by_temporal_datetime_range(tmp_path):
    body = (
        _client_with_filter_fields(tmp_path)
        .get(
            "/api/documents/tabular",
            params={"filters": json.dumps([{"field": "created_at", "op": "range", "min": "2021-01-01T00:00:00"}])},
        )
        .json()
    )

    assert {d["id"] for d in body["documents"]} == {"doc1", "doc2"}


def test_tabular_route_combines_multiple_filters(tmp_path):
    body = (
        _client(tmp_path)
        .get(
            "/api/documents/tabular",
            params={
                "filters": json.dumps(
                    [
                        {"field": "predictions", "op": "in", "values": ["a"]},
                        {"field": "confidence", "op": "range", "min": 0.2},
                    ]
                )
            },
        )
        .json()
    )

    assert {d["id"] for d in body["documents"]} == {"doc2"}


def test_tabular_route_filter_rejects_unknown_field(tmp_path):
    response = _client(tmp_path).get(
        "/api/documents/tabular",
        params={"filters": json.dumps([{"field": "nope", "op": "in", "values": ["a"]}])},
    )
    assert response.status_code == 400


def test_tabular_route_filter_rejects_op_type_mismatch(tmp_path):
    response = _client(tmp_path).get(
        "/api/documents/tabular",
        params={"filters": json.dumps([{"field": "confidence", "op": "in", "values": ["0.1"]}])},
    )
    assert response.status_code == 400


def test_fields_route_includes_filter_metadata(tmp_path):
    body = _client(tmp_path).get("/api/documents/fields").json()

    fields = {f["name"]: f for f in body["fields"]}
    assert fields["predictions"]["values"] == ["a", "b"]
    assert fields["confidence"]["min"] == 0.1
    assert fields["confidence"]["max"] == 0.3


def test_scatter_route_filters_by_extra_field(tmp_path):
    body = (
        _client(tmp_path)
        .get(
            "/api/documents/scatter",
            params={
                "field": "embedding",
                "filters": json.dumps([{"field": "predictions", "op": "in", "values": ["b"]}]),
            },
        )
        .json()
    )

    assert {p["documentId"] for p in body["points"]} == {"doc1"}


def test_scatter_route_lists_fields_with_no_query_params(tmp_path):
    body = _client(tmp_path).get("/api/documents/scatter").json()

    assert body["points"] == []
    assert body["fields"] == [
        {"name": "embedding", "type": "point_2d", "values": None, "min": None, "max": None},
        {"name": "confidence", "type": "score", "values": None, "min": None, "max": None},
        {"name": "readability", "type": "score", "values": None, "min": None, "max": None},
        {"name": "predictions", "type": "label", "values": None, "min": None, "max": None},
        {"name": "topic", "type": "group", "values": None, "min": None, "max": None},
    ]


def test_scatter_route_returns_points_2d_field(tmp_path):
    body = _client(tmp_path).get("/api/documents/scatter", params={"field": "embedding"}).json()

    points = {p["documentId"]: p for p in body["points"]}
    assert set(points) == {"doc0", "doc1"}  # doc2's value was None
    assert points["doc1"] == {"documentId": "doc1", "x": 1.0, "y": 1.0, "text": "second", "group": None}


def test_scatter_route_returns_score_pair(tmp_path):
    client = _client(tmp_path)
    body = client.get("/api/documents/scatter", params={"xField": "confidence", "yField": "readability"}).json()

    points = {p["documentId"]: p for p in body["points"]}
    assert set(points) == {"doc0", "doc2"}  # doc1's readability was None
    assert points["doc0"] == {"documentId": "doc0", "x": 0.1, "y": 50.0, "text": "first", "group": None}


def test_scatter_route_attaches_group_for_points_2d(tmp_path):
    client = _client(tmp_path)
    body = client.get("/api/documents/scatter", params={"field": "embedding", "colorField": "topic"}).json()

    points = {p["documentId"]: p for p in body["points"]}
    assert points["doc0"]["group"] == "weather"
    assert points["doc1"]["group"] == "politics"


def test_scatter_route_attaches_group_for_score_pair(tmp_path):
    client = _client(tmp_path)
    body = client.get(
        "/api/documents/scatter",
        params={"xField": "confidence", "yField": "readability", "colorField": "topic"},
    ).json()

    points = {p["documentId"]: p for p in body["points"]}
    assert points["doc0"]["group"] == "weather"
    assert points["doc2"]["group"] is None  # doc2 has no "topic" value; the join keeps the point anyway


def test_scatter_route_rejects_conflicting_params(tmp_path):
    response = _client(tmp_path).get("/api/documents/scatter", params={"field": "embedding", "xField": "confidence"})
    assert response.status_code == 400


def test_scatter_route_rejects_partial_pair(tmp_path):
    response = _client(tmp_path).get("/api/documents/scatter", params={"xField": "confidence"})
    assert response.status_code == 400


def test_fields_route_returns_full_field_list(tmp_path):
    body = _client(tmp_path).get("/api/documents/fields").json()

    assert body["fields"] == [
        {"name": "predictions", "type": "label", "values": ["a", "b"], "min": None, "max": None},
        {"name": "confidence", "type": "score", "values": None, "min": 0.1, "max": 0.3},
        {"name": "readability", "type": "score", "values": None, "min": 50.0, "max": 70.0},
        {"name": "topic", "type": "group", "values": ["politics", "weather"], "min": None, "max": None},
        {"name": "embedding", "type": "point_2d", "values": None, "min": None, "max": None},
    ]


def test_document_route_returns_one_document(tmp_path):
    body = _client(tmp_path).get("/api/documents/doc1").json()

    assert body == {
        "id": "doc1",
        "text": "second",
        "values": {"predictions": "b", "confidence": 0.2, "topic": "politics", "embedding": [1.0, 1.0]},
        "note": "",
    }


def test_document_route_for_unknown_document_is_404(tmp_path):
    assert _client(tmp_path).get("/api/documents/nope").status_code == 404


def test_note_is_saved_replaced_and_returned(tmp_path):
    client = _client(tmp_path)

    assert client.put("/api/documents/doc1/note", json={"text": "first draft"}).status_code == 204
    assert client.put("/api/documents/doc1/note", json={"text": "revised"}).status_code == 204

    notes = {d["id"]: d["note"] for d in client.get("/api/documents/tabular").json()["documents"]}
    assert notes == {"doc0": "", "doc1": "revised", "doc2": ""}


def test_note_for_unknown_document_is_404(tmp_path):
    assert _client(tmp_path).put("/api/documents/nope/note", json={"text": "x"}).status_code == 404


def test_scatter_route_colors_by_label_field(tmp_path):
    body = (
        _client(tmp_path)
        .get("/api/documents/scatter", params={"field": "embedding", "colorField": "predictions"})
        .json()
    )

    points = {p["documentId"]: p for p in body["points"]}
    assert points["doc1"]["group"] == "b"


def test_strip_route_returns_points_with_row_and_color(tmp_path):
    body = (
        _client(tmp_path)
        .get("/api/documents/strip", params={"xField": "confidence", "rowField": "predictions", "colorField": "topic"})
        .json()
    )

    points = {p["documentId"]: p for p in body["points"]}
    assert points["doc0"] == {"documentId": "doc0", "x": 0.1, "text": "first", "row": "a", "color": "weather"}
    assert points["doc2"]["color"] is None  # doc2 has no "topic" value; the join keeps the point anyway


def test_strip_route_omits_documents_missing_x(tmp_path):
    body = _client(tmp_path).get("/api/documents/strip", params={"xField": "readability", "rowField": "topic"}).json()

    points = {p["documentId"]: p for p in body["points"]}
    assert set(points) == {"doc0", "doc2"}  # doc1's readability was None
    assert points["doc2"]["row"] is None  # doc2 has no "topic"; the point is kept anyway
    assert all(p["color"] is None for p in body["points"])


def test_strip_route_filters(tmp_path):
    body = (
        _client(tmp_path)
        .get(
            "/api/documents/strip",
            params={
                "xField": "confidence",
                "rowField": "predictions",
                "filters": json.dumps([{"field": "predictions", "op": "in", "values": ["a"]}]),
            },
        )
        .json()
    )

    assert {p["documentId"] for p in body["points"]} == {"doc0", "doc2"}


def test_strip_route_rejects_non_categorical_row_field(tmp_path):
    response = _client(tmp_path).get("/api/documents/strip", params={"xField": "confidence", "rowField": "readability"})
    assert response.status_code == 400


def test_strip_route_requires_row_field(tmp_path):
    response = _client(tmp_path).get("/api/documents/strip", params={"xField": "confidence"})
    assert response.status_code == 422


def test_crosstab_route_counts_value_pairs(tmp_path):
    body = (
        _client(tmp_path).get("/api/documents/crosstab", params={"rowField": "predictions", "colField": "topic"}).json()
    )

    cells = {(c["row"], c["col"]): c["count"] for c in body["cells"]}
    # doc2 has a prediction but no topic, so it counts under a None column.
    assert cells == {("a", "weather"): 1, ("b", "politics"): 1, ("a", None): 1}


def test_crosstab_route_rejects_non_categorical_field(tmp_path):
    response = _client(tmp_path).get(
        "/api/documents/crosstab", params={"rowField": "predictions", "colField": "confidence"}
    )
    assert response.status_code == 400
