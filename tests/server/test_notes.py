import json

from fastapi.testclient import TestClient

import sourcetext.db as db
from sourcetext.notes import NotesFile, text_hash
from sourcetext.server.app import app


def test_note_is_saved_replaced_and_returned(client):
    assert client.put("/api/documents/doc1/note", json={"text": "first draft"}).status_code == 204
    assert client.put("/api/documents/doc1/note", json={"text": "revised"}).status_code == 204

    notes = {d["id"]: d["note"] for d in client.get("/api/documents/tabular").json()["documents"]}
    assert notes == {"doc0": "", "doc1": "revised", "doc2": ""}


def test_note_for_unknown_document_is_404(client):
    assert client.put("/api/documents/nope/note", json={"text": "x"}).status_code == 404


def test_get_note_before_and_after_saving(client):
    assert client.get("/api/documents/doc1/note").json() == {"text": ""}
    client.put("/api/documents/doc1/note", json={"text": "a note"})
    assert client.get("/api/documents/doc1/note").json() == {"text": "a note"}


def test_get_note_for_unknown_document_is_404(client):
    assert client.get("/api/documents/nope/note").status_code == 404


def test_get_note_finds_notes_matched_by_text_hash(tmp_path):
    # Records written for another corpus order: their ids don't match, their text hashes do.
    create_session = db.get_sessionmaker(f"duckdb:///{tmp_path / 'hash.duckdb'}")
    with create_session() as session:
        db.add_documents(session, ["d0", "d1", "d2", "d3"], ["alpha", "beta", "alpha", "gamma"])
        session.commit()
    app.state.db_sessionmaker = create_session
    app.state.notes_file = NotesFile(match_by="text")
    client = TestClient(app)
    notes_path = tmp_path / "notes.jsonl"
    stamp = "2026-01-01T00:00:00+00:00"
    notes_path.write_text(
        "".join(
            json.dumps({"document_id": old_id, "text_hash": text_hash(text), "note": note, "updated_at": stamp}) + "\n"
            for old_id, text, note in [("old-7", "alpha", "alpha note"), ("old-1", "gamma", "gamma note")]
        )
    )

    assert client.put("/api/notes/file", json={"path": str(notes_path)}).status_code == 200

    notes = {i: client.get(f"/api/documents/{i}/note").json()["text"] for i in ["d0", "d1", "d2", "d3"]}
    assert notes == {"d0": "alpha note", "d1": "", "d2": "alpha note", "d3": "gamma note"}


def test_note_without_a_notes_file_is_409(client):
    app.state.notes_file = NotesFile()

    assert client.put("/api/documents/doc1/note", json={"text": "x"}).status_code == 409
    assert client.get("/api/documents/doc1").json()["note"] == ""


def test_note_that_cannot_be_written_to_the_file_is_not_kept(client, tmp_path):
    app.state.notes_file = NotesFile(tmp_path / "missing_dir" / "notes.jsonl")

    assert client.put("/api/documents/doc1/note", json={"text": "x"}).status_code == 500
    assert client.get("/api/documents/doc1").json()["note"] == ""


def test_empty_note_removes_it(client):
    client.put("/api/documents/doc1/note", json={"text": "draft"})
    client.put("/api/documents/doc1/note", json={"text": ""})

    assert client.get("/api/documents/doc1").json()["note"] == ""


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_notes_file_status_without_a_file(client):
    app.state.notes_file = NotesFile()
    body = client.get("/api/notes/file").json()

    assert body["path"] is None
    assert body["suggestedPath"].endswith("sourcetext_notes.jsonl")


def test_switching_notes_file_writes_existing_notes_and_later_ones(client, tmp_path):
    client.put("/api/documents/doc0/note", json={"text": "before"})

    notes_path = tmp_path / "notes.jsonl"
    body = client.put("/api/notes/file", json={"path": str(notes_path)}).json()
    assert body["path"] == str(notes_path.resolve())
    assert body["load"] == {"loaded": 0, "messages": []}
    assert [r["note"] for r in _read_jsonl(notes_path)] == ["before"]

    client.put("/api/documents/doc1/note", json={"text": "after"})
    assert [(r["document_id"], r["note"]) for r in _read_jsonl(notes_path)] == [("doc0", "before"), ("doc1", "after")]


def test_choosing_an_existing_notes_file_merges_it(client, tmp_path):
    notes_path = tmp_path / "notes.jsonl"
    stamp = "2026-01-01T00:00:00+00:00"
    notes_path.write_text(
        json.dumps({"document_id": "doc0", "text_hash": "x", "note": "from file", "updated_at": stamp})
        + "\n"
        + json.dumps({"document_id": "doc1", "text_hash": "x", "note": "overridden", "updated_at": stamp})
        + "\n"
    )
    # The client fixture's NotesFile matches by text; match by id here, since the hashes above are made up.
    app.state.notes_file = NotesFile(tmp_path / "session_notes.jsonl", match_by="id")
    client.put("/api/documents/doc1/note", json={"text": "from session"})

    body = client.put("/api/notes/file", json={"path": str(notes_path)}).json()

    assert body["load"]["loaded"] == 1
    assert len(body["load"]["messages"]) == 2  # changed text, and one note merged with the session's
    notes = {d["id"]: d["note"] for d in client.get("/api/documents/tabular").json()["documents"]}
    assert notes == {"doc0": "from file", "doc1": "overridden\n\n---\n\nfrom session", "doc2": ""}


def test_unusable_notes_file_is_400(client, tmp_path):
    (tmp_path / "bad.jsonl").write_text("not json\n")

    assert client.put("/api/notes/file", json={"path": ""}).status_code == 400
    assert client.put("/api/notes/file", json={"path": str(tmp_path / "missing" / "n.jsonl")}).status_code == 400
    response = client.put("/api/notes/file", json={"path": str(tmp_path / "bad.jsonl")})
    assert response.status_code == 400
    assert "line 1" in response.json()["detail"]
    # A failed choice leaves the previous file in place.
    assert client.get("/api/notes/file").json()["path"] == str((tmp_path / "session_notes.jsonl").resolve())
    assert client.put("/api/notes/file", json={"path": None}).status_code == 422
