import json

import sourcetext.db as db
from sourcetext.server.app import app


def test_tabular_route_returns_fields_and_values(client):
    body = client.get("/api/documents/tabular").json()

    assert body["total"] == 3
    assert body["fields"] == [
        {"name": "predictions", "type": "label", "values": ["a", "b"], "min": None, "max": None, "definitions": None},
        {
            "name": "topic",
            "type": "label",
            "values": ["politics", "weather"],
            "min": None,
            "max": None,
            "definitions": None,
        },
        {"name": "confidence", "type": "score", "values": None, "min": 0.1, "max": 0.3, "definitions": None},
        {"name": "readability", "type": "score", "values": None, "min": 50.0, "max": 70.0, "definitions": None},
        {"name": "embedding", "type": "point_2d", "values": None, "min": None, "max": None, "definitions": None},
    ]
    assert [d["id"] for d in body["documents"]] == ["doc0", "doc1", "doc2"]
    assert body["documents"][1] == {
        "id": "doc1",
        "text": "second",
        "values": {"predictions": "b", "confidence": 0.2, "topic": "politics", "embedding": [1.0, 1.0]},
        "note": "",
    }


def test_tabular_route_paginates(client):
    body = client.get("/api/documents/tabular", params={"limit": 2, "offset": 2}).json()

    assert body["total"] == 3
    assert [d["id"] for d in body["documents"]] == ["doc2"]


def test_tabular_route_sorts_by_id_desc(client):
    body = client.get("/api/documents/tabular", params={"sortField": "id", "sortDir": "desc"}).json()

    assert [d["id"] for d in body["documents"]] == ["doc2", "doc1", "doc0"]


def test_tabular_route_sorts_by_score_field(client):
    body = client.get("/api/documents/tabular", params={"sortField": "confidence", "sortDir": "desc"}).json()

    assert [d["id"] for d in body["documents"]] == ["doc2", "doc1", "doc0"]


def test_tabular_route_sort_puts_missing_values_last(client):
    # doc1's "readability" is None regardless of ascending or descending sort direction.

    body = client.get("/api/documents/tabular", params={"sortField": "readability"}).json()
    assert [d["id"] for d in body["documents"]] == ["doc0", "doc2", "doc1"]

    body = client.get("/api/documents/tabular", params={"sortField": "readability", "sortDir": "desc"}).json()
    assert [d["id"] for d in body["documents"]] == ["doc2", "doc0", "doc1"]


def test_tabular_route_rejects_unsortable_field(client):
    response = client.get("/api/documents/tabular", params={"sortField": "embedding"})
    assert response.status_code == 400


def test_tabular_route_rejects_unknown_sort_field(client):
    response = client.get("/api/documents/tabular", params={"sortField": "nope"})
    assert response.status_code == 400


def test_tabular_route_filters_by_label_in(client):
    body = client.get(
        "/api/documents/tabular",
        params={"filters": json.dumps([{"field": "predictions", "op": "in", "values": ["a"]}])},
    ).json()

    assert {d["id"] for d in body["documents"]} == {"doc0", "doc2"}
    assert body["total"] == 2


def test_tabular_route_filters_by_score_range(client):
    body = client.get(
        "/api/documents/tabular",
        params={"filters": json.dumps([{"field": "confidence", "op": "range", "min": 0.2}])},
    ).json()

    assert {d["id"] for d in body["documents"]} == {"doc1", "doc2"}


def _search_ids(client, filters) -> set[str]:
    response = client.get("/api/documents/tabular", params={"filters": json.dumps(filters)})
    assert response.status_code == 200
    return {d["id"] for d in response.json()["documents"]}


def _search(text: str, *fields: str) -> dict:
    return {"op": "search", "text": text, "fields": list(fields)}


def test_search_filter_on_a_text_field(filter_fields_client):
    assert _search_ids(filter_fields_client, [_search("needs", "editor_note")]) == {"doc0", "doc2"}


def test_search_filter_on_text_searches_source_text_only(filter_fields_client):
    assert _search_ids(filter_fields_client, [_search("IR", "text")]) == {"doc0", "doc2"}
    # "good" is only in a text field, not in any source text.
    assert _search_ids(filter_fields_client, [_search("good", "text")]) == set()


def test_search_filter_matches_any_of_its_fields(filter_fields_client):
    assert _search_ids(filter_fields_client, [_search("GOOD", "text", "editor_note")]) == {"doc1"}
    assert _search_ids(filter_fields_client, [_search("third", "text", "editor_note")]) == {"doc2"}


def test_search_filter_treats_wildcards_literally(filter_fields_client):
    assert _search_ids(filter_fields_client, [_search("%", "text", "editor_note")]) == set()
    assert _search_ids(filter_fields_client, [_search("_", "editor_note")]) == set()


def test_invalid_search_filters_are_rejected(filter_fields_client):
    for search in (_search("x", "pub_year"), _search("x", "missing"), _search("x"), _search("", "text")):
        response = filter_fields_client.get("/api/documents/tabular", params={"filters": json.dumps([search])})
        assert response.status_code == 400, search


def test_field_filters_require_a_field(client):
    response = client.get("/api/documents/tabular", params={"filters": json.dumps([{"op": "in", "values": ["a"]}])})

    assert response.status_code == 400


def test_tabular_route_filters_by_temporal_year_range(filter_fields_client):
    body = filter_fields_client.get(
        "/api/documents/tabular",
        params={"filters": json.dumps([{"field": "pub_year", "op": "range", "min": 2021}])},
    ).json()

    assert {d["id"] for d in body["documents"]} == {"doc1", "doc2"}


def test_tabular_route_filters_by_temporal_date_range(filter_fields_client):
    body = filter_fields_client.get(
        "/api/documents/tabular",
        params={"filters": json.dumps([{"field": "pub_date", "op": "range", "max": "2021-12-31"}])},
    ).json()

    assert {d["id"] for d in body["documents"]} == {"doc0", "doc1"}


def test_tabular_route_filters_by_temporal_datetime_range(filter_fields_client):
    body = filter_fields_client.get(
        "/api/documents/tabular",
        params={"filters": json.dumps([{"field": "created_at", "op": "range", "min": "2021-01-01T00:00:00"}])},
    ).json()

    assert {d["id"] for d in body["documents"]} == {"doc1", "doc2"}


def test_tabular_route_combines_multiple_filters(client):
    body = client.get(
        "/api/documents/tabular",
        params={
            "filters": json.dumps(
                [
                    {"field": "predictions", "op": "in", "values": ["a"]},
                    {"field": "confidence", "op": "range", "min": 0.2},
                ]
            )
        },
    ).json()

    assert {d["id"] for d in body["documents"]} == {"doc2"}


def test_tabular_route_filter_rejects_unknown_field(client):
    response = client.get(
        "/api/documents/tabular",
        params={"filters": json.dumps([{"field": "nope", "op": "in", "values": ["a"]}])},
    )
    assert response.status_code == 400


def test_tabular_route_filter_rejects_op_type_mismatch(client):
    response = client.get(
        "/api/documents/tabular",
        params={"filters": json.dumps([{"field": "confidence", "op": "in", "values": ["0.1"]}])},
    )
    assert response.status_code == 400


def test_fields_route_includes_filter_metadata(client):
    body = client.get("/api/documents/fields").json()

    fields = {f["name"]: f for f in body["fields"]}
    assert fields["predictions"]["values"] == ["a", "b"]
    assert fields["confidence"]["min"] == 0.1
    assert fields["confidence"]["max"] == 0.3


def test_fields_route_returns_full_field_list(client):
    body = client.get("/api/documents/fields").json()

    assert body["fields"] == [
        {"name": "predictions", "type": "label", "values": ["a", "b"], "min": None, "max": None, "definitions": None},
        {
            "name": "topic",
            "type": "label",
            "values": ["politics", "weather"],
            "min": None,
            "max": None,
            "definitions": None,
        },
        {"name": "confidence", "type": "score", "values": None, "min": 0.1, "max": 0.3, "definitions": None},
        {"name": "readability", "type": "score", "values": None, "min": 50.0, "max": 70.0, "definitions": None},
        {"name": "embedding", "type": "point_2d", "values": None, "min": None, "max": None, "definitions": None},
    ]


def test_document_route_returns_one_document(client):
    body = client.get("/api/documents/doc1").json()

    assert body == {
        "id": "doc1",
        "text": "second",
        "values": {"predictions": "b", "confidence": 0.2, "topic": "politics", "embedding": [1.0, 1.0]},
        "note": "",
    }


def test_document_route_for_unknown_document_is_404(client):
    assert client.get("/api/documents/nope").status_code == 404


def test_fields_routes_include_label_definitions(client):
    with app.state.db_sessionmaker() as session:
        db.add_label_definitions(session, "topic", {"weather": "Rain and sun", "politics": {"vote": 0.4}})
        session.commit()
    expected = {"weather": "Rain and sun", "politics": {"vote": 0.4}}

    fields = {f["name"]: f for f in client.get("/api/documents/fields").json()["fields"]}
    assert fields["topic"]["definitions"] == expected
    assert fields["predictions"]["definitions"] is None

    plot_fields = {f["name"]: f for f in client.get("/api/documents/scatter").json()["fields"]}
    assert plot_fields["topic"]["definitions"] == expected
