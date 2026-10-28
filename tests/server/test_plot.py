import json


def test_scatter_route_filters_by_extra_field(client):
    body = client.get(
        "/api/documents/scatter",
        params={
            "field": "embedding",
            "filters": json.dumps([{"field": "predictions", "op": "in", "values": ["b"]}]),
        },
    ).json()

    assert {p["documentId"] for p in body["points"]} == {"doc1"}


def test_scatter_route_lists_fields_with_no_query_params(client):
    body = client.get("/api/documents/scatter").json()

    assert body["points"] == []
    assert body["fields"] == [
        {"name": "embedding", "type": "point_2d", "values": None, "min": None, "max": None, "definitions": None},
        {"name": "confidence", "type": "score", "values": None, "min": None, "max": None, "definitions": None},
        {"name": "readability", "type": "score", "values": None, "min": None, "max": None, "definitions": None},
        {"name": "predictions", "type": "label", "values": None, "min": None, "max": None, "definitions": None},
        {"name": "topic", "type": "label", "values": None, "min": None, "max": None, "definitions": None},
    ]


def test_scatter_route_returns_points_2d_field(client):
    body = client.get("/api/documents/scatter", params={"field": "embedding"}).json()

    points = {p["documentId"]: p for p in body["points"]}
    assert set(points) == {"doc0", "doc1"}  # doc2's value was None
    assert points["doc1"] == {"documentId": "doc1", "x": 1.0, "y": 1.0, "text": "second", "group": None}


def test_scatter_route_returns_score_pair(client):
    body = client.get("/api/documents/scatter", params={"xField": "confidence", "yField": "readability"}).json()

    points = {p["documentId"]: p for p in body["points"]}
    assert set(points) == {"doc0", "doc2"}  # doc1's readability was None
    assert points["doc0"] == {"documentId": "doc0", "x": 0.1, "y": 50.0, "text": "first", "group": None}


def test_scatter_route_attaches_group_for_points_2d(client):
    body = client.get("/api/documents/scatter", params={"field": "embedding", "colorField": "topic"}).json()

    points = {p["documentId"]: p for p in body["points"]}
    assert points["doc0"]["group"] == "weather"
    assert points["doc1"]["group"] == "politics"


def test_scatter_route_attaches_group_for_score_pair(client):
    body = client.get(
        "/api/documents/scatter",
        params={"xField": "confidence", "yField": "readability", "colorField": "topic"},
    ).json()

    points = {p["documentId"]: p for p in body["points"]}
    assert points["doc0"]["group"] == "weather"
    assert points["doc2"]["group"] is None  # doc2 has no "topic" value; the join keeps the point anyway


def test_scatter_route_rejects_conflicting_params(client):
    response = client.get("/api/documents/scatter", params={"field": "embedding", "xField": "confidence"})
    assert response.status_code == 400


def test_scatter_route_rejects_partial_pair(client):
    response = client.get("/api/documents/scatter", params={"xField": "confidence"})
    assert response.status_code == 400


def test_scatter_route_colors_by_label_field(client):
    body = client.get("/api/documents/scatter", params={"field": "embedding", "colorField": "predictions"}).json()

    points = {p["documentId"]: p for p in body["points"]}
    assert points["doc1"]["group"] == "b"


def test_strip_route_returns_points_with_row_and_color(client):
    body = client.get(
        "/api/documents/strip", params={"xField": "confidence", "rowField": "predictions", "colorField": "topic"}
    ).json()

    points = {p["documentId"]: p for p in body["points"]}
    assert points["doc0"] == {"documentId": "doc0", "x": 0.1, "text": "first", "row": "a", "color": "weather"}
    assert points["doc2"]["color"] is None  # doc2 has no "topic" value; the join keeps the point anyway


def test_strip_route_omits_documents_missing_x(client):
    body = client.get("/api/documents/strip", params={"xField": "readability", "rowField": "topic"}).json()

    points = {p["documentId"]: p for p in body["points"]}
    assert set(points) == {"doc0", "doc2"}  # doc1's readability was None
    assert points["doc2"]["row"] is None  # doc2 has no "topic"; the point is kept anyway
    assert all(p["color"] is None for p in body["points"])


def test_strip_route_filters(client):
    body = client.get(
        "/api/documents/strip",
        params={
            "xField": "confidence",
            "rowField": "predictions",
            "filters": json.dumps([{"field": "predictions", "op": "in", "values": ["a"]}]),
        },
    ).json()

    assert {p["documentId"] for p in body["points"]} == {"doc0", "doc2"}


def test_strip_route_rejects_non_categorical_row_field(client):
    response = client.get("/api/documents/strip", params={"xField": "confidence", "rowField": "readability"})
    assert response.status_code == 400


def test_strip_route_requires_row_field(client):
    response = client.get("/api/documents/strip", params={"xField": "confidence"})
    assert response.status_code == 422
