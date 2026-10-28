import json


def _span_filter(**kwargs) -> dict:
    return {"filters": json.dumps([{"field": "entities", "op": "span", **kwargs}])}


def test_fields_include_span_fields_with_labels_and_score_bounds(spans_client):
    body = spans_client.get("/api/documents/fields").json()

    assert body["fields"][-1] == {
        "name": "entities",
        "type": "span",
        "values": ["LOC", "PER", None],
        "min": 0.4,
        "max": 0.9,
        "definitions": None,
    }


def test_spans_route_counts_labels_and_types(spans_client):
    body = spans_client.get("/api/spans").json()

    assert body["fields"] == ["entities"]
    assert body["field"] == "entities"
    assert body["labels"] == [
        {"label": "PER", "spans": 4, "documents": 3},
        {"label": "LOC", "spans": 1, "documents": 1},
        {"label": None, "spans": 1, "documents": 1},
    ]
    # "Obama" and "Barack Obama" share a norm text, so they're one type with two
    # variants; covered text is cut by character offsets, so "Ærø" lines up.
    assert body["types"] == [
        {"text": "Barack Obama", "label": "PER", "spans": 2, "documents": 2, "variants": 2},
        {"text": "Berlin", "label": "LOC", "spans": 1, "documents": 1, "variants": 1},
        {"text": "Merkel", "label": "PER", "spans": 1, "documents": 1, "variants": 1},
        {"text": "Obama", "label": "PER", "spans": 1, "documents": 1, "variants": 1},
        {"text": "Ærø", "label": None, "spans": 1, "documents": 1, "variants": 1},
    ]
    assert body["totalTypes"] == 5


def test_spans_route_prunes_spans_by_the_fields_span_filter(spans_client):
    # Labels counts ignore the label condition, but not the score one.
    body = spans_client.get("/api/spans", params=_span_filter(values=["LOC"], min=0.5)).json()
    assert body["labels"] == [{"label": "PER", "spans": 3, "documents": 3}]
    assert body["types"] == []

    body = spans_client.get("/api/spans", params=_span_filter(min=0.75)).json()
    assert [(t["text"], t["spans"]) for t in body["types"]] == [("Barack Obama", 2)]

    # Search matches the span text or the norm text.
    body = spans_client.get("/api/spans", params=_span_filter(text="barack")).json()
    assert [(t["text"], t["spans"]) for t in body["types"]] == [("Barack Obama", 2)]

    body = spans_client.get("/api/spans", params=_span_filter(values=[None])).json()
    assert [t["text"] for t in body["types"]] == ["Ærø"]

    body = spans_client.get("/api/spans", params={"limit": 1}).json()
    assert len(body["types"]) == 1
    assert body["totalTypes"] == 5


def test_spans_route_applies_other_fields_filters(spans_client):
    filters = json.dumps([{"field": "predictions", "op": "in", "values": ["a"]}])
    body = spans_client.get("/api/spans", params={"filters": filters}).json()

    assert body["labels"] == [{"label": "PER", "spans": 2, "documents": 1}]
    assert [t["text"] for t in body["types"]] == ["Barack Obama", "Merkel"]


def test_spans_route_without_span_fields(client):
    body = client.get("/api/spans").json()

    assert body == {"fields": [], "field": None, "labels": [], "types": [], "totalTypes": 0}


def test_spans_route_rejects_non_span_field(spans_client):
    response = spans_client.get("/api/spans", params={"field": "predictions"})

    assert response.status_code == 400


def test_tabular_route_span_filter(spans_client):
    def ids(**kwargs):
        body = spans_client.get("/api/documents/tabular", params=_span_filter(**kwargs)).json()
        return [d["id"] for d in body["documents"]]

    assert ids() == ["doc0", "doc1", "doc3"]
    assert ids(values=["LOC"]) == ["doc1"]
    assert ids(values=[None]) == ["doc3"]
    assert ids(values=["LOC", None]) == ["doc1", "doc3"]
    assert ids(min=0.75) == ["doc0", "doc1"]
    assert ids(max=0.5) == ["doc0"]
    assert ids(text="BARACK") == ["doc0", "doc1"]
    assert ids(type_text="Barack Obama", values=["PER"]) == ["doc0", "doc1"]
    assert ids(type_text="Obama") == ["doc3"]
    response = spans_client.get(
        "/api/documents/tabular", params={"filters": json.dumps([{"field": "predictions", "op": "span"}])}
    )
    assert response.status_code == 400


def test_tabular_route_span_values_are_types_pruned_by_the_span_filter(spans_client):
    documents = spans_client.get("/api/documents/tabular").json()["documents"]
    assert documents[0]["values"]["entities"] == [
        {"text": "Barack Obama", "label": "PER", "count": 1},
        {"text": "Merkel", "label": "PER", "count": 1},
    ]
    assert "entities" not in documents[2]["values"]

    documents = spans_client.get("/api/documents/tabular", params=_span_filter(min=0.5)).json()["documents"]
    assert documents[0]["values"]["entities"] == [{"text": "Barack Obama", "label": "PER", "count": 1}]


def test_document_spans_route(spans_client):
    assert spans_client.get("/api/documents/doc1/spans").json() == {
        "spans": [
            {
                "field": "entities",
                "start": 0,
                "end": 12,
                "text": "Barack Obama",
                "normText": "Barack Obama",
                "label": "PER",
                "score": 0.8,
            },
            {
                "field": "entities",
                "start": 22,
                "end": 28,
                "text": "Berlin",
                "normText": None,
                "label": "LOC",
                "score": None,
            },
        ]
    }
    assert spans_client.get("/api/documents/doc2/spans").json() == {"spans": []}
    assert spans_client.get("/api/documents/missing/spans").status_code == 404


def test_document_spans_route_prunes_by_span_filters(spans_client):
    body = spans_client.get("/api/documents/doc0/spans", params=_span_filter(min=0.5)).json()
    assert [s["text"] for s in body["spans"]] == ["Obama"]
    # Filters on other fields don't prune spans.
    filters = json.dumps([{"field": "predictions", "op": "in", "values": ["b"]}])
    body = spans_client.get("/api/documents/doc0/spans", params={"filters": filters}).json()
    assert len(body["spans"]) == 2
