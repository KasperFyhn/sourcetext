def test_crosstab_route_counts_value_pairs(client):
    body = client.get("/api/documents/crosstab", params={"rowField": "predictions", "colField": "topic"}).json()

    cells = {(c["row"], c["col"]): c["count"] for c in body["cells"]}
    # doc2 has a prediction but no topic, so it counts under a None column.
    assert cells == {("a", "weather"): 1, ("b", "politics"): 1, ("a", None): 1}


def test_crosstab_route_rejects_non_categorical_field(client):
    response = client.get("/api/documents/crosstab", params={"rowField": "predictions", "colField": "confidence"})
    assert response.status_code == 400
