import pytest
from sqlalchemy import func, select

import sourcetext.db as db
from sourcetext.db.schema import Document, Label, Span


def test_add_functions_return_how_many_rows_they_inserted():
    with db.get_sessionmaker()() as session:
        assert db.add_documents(session, ["a", "b"], ["x", "y"]) == 2
        assert db.add_labels(session, "pred", ["a", "b"], ["p", None]) == 1
        assert db.add_spans(session, "ner", ["a", "b"], [[{"start": 0, "end": 1}], []]) == 1
        assert db.add_points_2d(session, "emb", ["a", "b"], [None, None]) == 0


def test_bulk_inserts_join_the_sessions_transaction():
    create_session = db.get_sessionmaker()
    with create_session() as session:
        db.add_documents(session, ["a"], ["x"])
        db.add_labels(session, "pred", ["a"], ["p"])
        session.rollback()
        assert session.execute(select(func.count()).select_from(Document)).scalar_one() == 0
        assert session.execute(select(func.count()).select_from(Label)).scalar_one() == 0


def test_span_on_a_missing_document_fails_rather_than_being_dropped():
    with db.get_sessionmaker()() as session:
        with pytest.raises(Exception):
            db.add_spans(session, "ner", ["missing"], [[{"start": 0, "end": 1}]])
        session.rollback()
        assert session.execute(select(func.count()).select_from(Span)).scalar_one() == 0
