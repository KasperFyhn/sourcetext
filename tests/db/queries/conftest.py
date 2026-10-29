import datetime as dt

import pytest

import sourcetext.db as db


@pytest.fixture
def session():
    """An in-memory DB with one field of each kind the query modules handle: label
    (with definitions), score, temporal date, text, point and span."""
    with db.get_sessionmaker()() as session:
        ids = ["d0", "d1", "d2"]
        db.add_documents(session, ids, ["Obama met Merkel.", "Merkel spoke.", "Nothing here."])
        db.add_labels(session, "prediction", ids, ["pos", "neg", "pos"])
        db.add_label_definitions(session, "prediction", {"pos": "Positive", "neg": "Negative"})
        db.add_scores(session, "confidence", ids, [0.9, 0.4, None])
        db.add_temporal_dates(
            session, "published", ids, [dt.date(2020, 1, 1), dt.date(2021, 1, 1), dt.date(2022, 1, 1)]
        )
        db.add_text(session, "comment", ids, ["Looks fine", None, "100% wrong"])
        db.add_points_2d(session, "embedding", ids, [(0.0, 1.0), (1.0, 0.0), None])
        db.add_spans(
            session,
            "entities",
            ids,
            [
                [
                    {"start": 0, "end": 5, "label": "PER", "score": 0.9, "norm_text": "Barack Obama"},
                    {"start": 10, "end": 16, "label": "PER", "score": 0.5},
                ],
                [{"start": 0, "end": 6}],
                [],
            ],
        )
        session.commit()
        yield session
