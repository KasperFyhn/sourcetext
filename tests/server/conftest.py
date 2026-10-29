import datetime as dt

import pytest
from fastapi.testclient import TestClient

import sourcetext.db as db
from sourcetext.notes import NotesFile
from sourcetext.server.app import app


@pytest.fixture
def client(tmp_path) -> TestClient:
    # File-backed: TestClient runs the app in another thread, and in-memory DuckDB isn't shared across threads.
    create_session = db.get_sessionmaker(f"duckdb:///{tmp_path / 'test.duckdb'}")
    with create_session() as session:
        ids = [f"doc{i}" for i in range(3)]
        db.add_documents(session, ids, ["first", "second", "third"])
        db.add_labels(session, "predictions", ids, ["a", "b", "a"])
        db.add_scores(session, "confidence", ids, [0.1, 0.2, 0.3])
        db.add_scores(session, "readability", ids, [50.0, None, 70.0])
        db.add_points_2d(session, "embedding", ids, [(0.0, 0.0), (1.0, 1.0), None])
        db.add_labels(session, "topic", ids, ["weather", "politics", None])
        session.commit()
    app.state.db_sessionmaker = create_session
    app.state.notes_file = NotesFile(tmp_path / "session_notes.jsonl")
    # Not used as a context manager, so the lifespan (static build check) is skipped.
    return TestClient(app)


@pytest.fixture
def filter_fields_client(tmp_path) -> TestClient:
    """A separate dataset (not `client`'s) adding text and all three temporal
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
    app.state.notes_file = NotesFile(tmp_path / "session_notes.jsonl")
    return TestClient(app)


@pytest.fixture
def spans_client(tmp_path) -> TestClient:
    """A separate dataset with a span field (NER-style: norm texts, scores, and an
    unlabelled span) and a label field to filter by."""
    create_session = db.get_sessionmaker(f"duckdb:///{tmp_path / 'spans.duckdb'}")
    with create_session() as session:
        ids = ["doc0", "doc1", "doc2", "doc3"]
        db.add_documents(
            session, ids, ["Obama met Merkel.", "Barack Obama spoke in Berlin.", "Nothing.", "Ærø og Obama."]
        )
        db.add_labels(session, "predictions", ids, ["a", "b", "a", "b"])
        db.add_spans(
            session,
            "entities",
            ids,
            [
                [
                    {"start": 0, "end": 5, "label": "PER", "score": 0.9, "norm_text": "Barack Obama"},
                    {"start": 10, "end": 16, "label": "PER", "score": 0.4},
                ],
                [
                    {"start": 0, "end": 12, "label": "PER", "score": 0.8, "norm_text": "Barack Obama"},
                    {"start": 22, "end": 28, "label": "LOC"},
                ],
                [],
                [{"start": 0, "end": 3}, {"start": 7, "end": 12, "label": "PER", "score": 0.7}],
            ],
        )
        session.commit()
    app.state.db_sessionmaker = create_session
    app.state.notes_file = NotesFile(tmp_path / "session_notes.jsonl")
    return TestClient(app)
