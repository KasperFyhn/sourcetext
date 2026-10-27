import json

import pytest

import sourcetext.db as db
from sourcetext import SourceText
from sourcetext.notes import DEFAULT_FILENAME, MERGE_SEPARATOR, NotesFile, text_hash

TEXTS = ["The cat sat.", "A dog ran.", "Birds fly south."]


def _session(tmp_path, texts=TEXTS, ids=None):
    create_session = db.get_sessionmaker(f"duckdb:///{tmp_path / 'test.duckdb'}")
    session = create_session()
    db.add_documents(session, ids or [str(i) for i in range(len(texts))], texts)
    session.commit()
    return session


def _notes(session):
    return {note.document_id: note.text for note in db.list_notes(session)}


def _record(document_id, text, note, updated_at="2026-01-01T00:00:00+00:00"):
    return {"document_id": document_id, "text_hash": text_hash(text), "note": note, "updated_at": updated_at}


def _write(path, records):
    path.write_text("".join(json.dumps(r) + "\n" for r in records))


def _read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_round_trip(tmp_path):
    path = tmp_path / "notes.jsonl"
    session = _session(tmp_path)
    db.set_note(session, "1", "a dog, not a cat")
    NotesFile(path).save(session)

    (record,) = _read(path)
    assert record["document_id"] == "1"
    assert record["text_hash"] == text_hash("A dog ran.")

    (tmp_path / "fresh").mkdir()
    fresh = _session(tmp_path / "fresh")
    report = NotesFile(path).load(fresh)
    assert report.loaded == 1
    assert _notes(fresh) == {"1": "a dog, not a cat"}


def test_text_matching_survives_reordering(tmp_path):
    path = tmp_path / "notes.jsonl"
    _write(path, [_record("0", "The cat sat.", "cat note")])
    session = _session(tmp_path, texts=list(reversed(TEXTS)))

    NotesFile(path, match_by="text").load(session)

    assert _notes(session) == {"2": "cat note"}


def test_id_matching_warns_about_changed_text(tmp_path):
    path = tmp_path / "notes.jsonl"
    _write(path, [_record("a", "The cat sat (old).", "note")])
    session = _session(tmp_path, ids=["a", "b", "c"])

    report = NotesFile(path, match_by="id").load(session)

    assert _notes(session) == {"a": "note"}
    assert report.changed_text == 1
    with pytest.warns(UserWarning, match="text has changed"):
        report.warn()


def test_duplicate_text_attaches_to_all(tmp_path):
    path = tmp_path / "notes.jsonl"
    _write(path, [_record("0", "same", "dup note")])
    session = _session(tmp_path, texts=["same", "other", "same"])

    report = NotesFile(path).load(session)

    assert _notes(session) == {"0": "dup note", "2": "dup note"}
    assert report.duplicate_text == 1


def test_latest_record_wins(tmp_path):
    path = tmp_path / "notes.jsonl"
    _write(
        path,
        [
            _record("0", "The cat sat.", "newer", "2026-02-01T00:00:00+00:00"),
            _record("5", "The cat sat.", "older", "2026-01-01T00:00:00+00:00"),
        ],
    )
    session = _session(tmp_path)

    NotesFile(path).load(session)

    assert _notes(session) == {"0": "newer"}


def test_orphans_are_kept_across_saves(tmp_path):
    path = tmp_path / "notes.jsonl"
    orphan = _record("99", "Not in this corpus.", "keep me")
    _write(path, [orphan])
    session = _session(tmp_path)
    notes_file = NotesFile(path)

    report = notes_file.load(session)
    db.set_note(session, "0", "new")
    notes_file.save(session)

    assert report.orphaned == 1
    assert orphan in _read(path)
    assert len(_read(path)) == 2


def test_empty_note_removes_record(tmp_path):
    path = tmp_path / "notes.jsonl"
    session = _session(tmp_path)
    notes_file = NotesFile(path)
    db.set_note(session, "0", "draft")
    notes_file.save(session)
    db.set_note(session, "0", "")
    notes_file.save(session)

    assert _read(path) == []


def test_malformed_line_names_line_number(tmp_path):
    path = tmp_path / "notes.jsonl"
    path.write_text(json.dumps(_record("0", "The cat sat.", "fine")) + "\n" + '{"document_id": "1"}\n')

    with pytest.raises(ValueError, match="line 2: missing key"):
        NotesFile(path).load(_session(tmp_path))


def test_set_path_merges_conflicting_notes_without_losing_either(tmp_path):
    path = tmp_path / "notes.jsonl"
    _write(
        path,
        [
            _record("0", "The cat sat.", "file 0"),
            _record("1", "A dog ran.", "file 1"),
            _record("2", "Birds fly south.", "same"),
        ],
    )
    session = _session(tmp_path)
    db.set_note(session, "1", "session 1")
    db.set_note(session, "2", "same")
    notes_file = NotesFile()

    report = notes_file.set_path(path, session)

    merged = "file 1" + MERGE_SEPARATOR + "session 1"  # older (file) text first
    assert (report.loaded, report.merged) == (1, 1)
    assert _notes(session) == {"0": "file 0", "1": merged, "2": "same"}
    assert {r["document_id"]: r["note"] for r in _read(path)} == {"0": "file 0", "1": merged, "2": "same"}


def test_sourcetext_picks_up_default_notes_file_in_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / DEFAULT_FILENAME, [_record("1", "A dog ran.", "dog note")])

    with pytest.warns(UserWarning, match="found in the working directory"):
        st = SourceText(TEXTS)

    assert _notes(st._session) == {"1": "dog note"}
    assert st._notes_file.path == (tmp_path / DEFAULT_FILENAME).resolve()


def test_sourcetext_loads_notes_file(tmp_path):
    path = tmp_path / "notes.jsonl"
    _write(path, [_record("b", "A dog ran.", "dog note")])

    st = SourceText(TEXTS, doc_id=["a", "b", "c"], notes_file=path)

    assert _notes(st._session) == {"b": "dog note"}


def test_sourcetext_with_missing_notes_file_creates_nothing_yet(tmp_path):
    path = tmp_path / "notes.jsonl"

    SourceText(TEXTS, notes_file=path)

    assert not path.exists()
