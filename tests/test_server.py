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
        session.commit()
    app.state.db_sessionmaker = create_session
    # Not used as a context manager, so the lifespan (static build check) is skipped.
    return TestClient(app)


def test_documents_route_returns_fields_and_values(tmp_path):
    body = _client(tmp_path).get("/api/documents").json()

    assert body["total"] == 3
    assert body["fields"] == [{"name": "predictions", "type": "label"}, {"name": "confidence", "type": "score"}]
    assert [d["id"] for d in body["documents"]] == ["doc0", "doc1", "doc2"]
    assert body["documents"][1] == {
        "id": "doc1",
        "text": "second",
        "values": {"predictions": "b", "confidence": 0.2},
        "note": "",
    }


def test_documents_route_paginates(tmp_path):
    body = _client(tmp_path).get("/api/documents", params={"limit": 2, "offset": 2}).json()

    assert body["total"] == 3
    assert [d["id"] for d in body["documents"]] == ["doc2"]


def test_note_is_saved_replaced_and_returned(tmp_path):
    client = _client(tmp_path)

    assert client.put("/api/documents/doc1/note", json={"text": "first draft"}).status_code == 204
    assert client.put("/api/documents/doc1/note", json={"text": "revised"}).status_code == 204

    notes = {d["id"]: d["note"] for d in client.get("/api/documents").json()["documents"]}
    assert notes == {"doc0": "", "doc1": "revised", "doc2": ""}


def test_note_for_unknown_document_is_404(tmp_path):
    assert _client(tmp_path).put("/api/documents/nope/note", json={"text": "x"}).status_code == 404
