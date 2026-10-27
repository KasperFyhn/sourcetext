from __future__ import annotations

import os
import warnings
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeAlias

import pandas as pd

import sourcetext.db as db
from sourcetext.notes import DEFAULT_FILENAME, NotesFile
from sourcetext.server.backgroundserver import BackgroundServer
from sourcetext.types import (
    IdType,
    IdValue,
    LabelType,
    LabelValue,
    Point2DType,
    Point2DValue,
    ScoreType,
    ScoreValue,
    SpanType,
    TemporalType,
    TextType,
    _PrimaryType,
    resolve_source,
)

# A bare `str` in these signatures always means "column name, resolved against
# data=" — this alias exists purely so the signature says that, rather than
# leaving a reader to infer it from a generic `str`.
ColumnName: TypeAlias = str


class SourceText:
    def __init__(
        self,
        text: ColumnName | Iterable[str] = None,
        *,
        data: pd.DataFrame | None = None,
        doc_id: ColumnName | Iterable[IdValue] | IdType | None = None,
        prediction: ColumnName | Iterable[LabelValue] | LabelType | None = None,
        confidence: ColumnName | Iterable[ScoreValue] | ScoreType | None = None,
        gold_label: ColumnName | Iterable[LabelValue] | LabelType | None = None,
        score: ColumnName | Iterable[ScoreValue] | ScoreType | None = None,
        embedding: ColumnName | Iterable[Point2DValue] | Point2DType | None = None,
        group: ColumnName | Iterable[LabelValue] | LabelType | None = None,
        group_definitions: dict[str, Any] = None,
        notes_file: str | os.PathLike | None = None,
        **fields: LabelType | ScoreType | TemporalType | TextType | Point2DType | SpanType,
    ) -> None:
        self._validate_mode(text, data)

        # Init DB
        self._create_session = db.get_sessionmaker()
        self._session = self._create_session()

        # resolve documents and add to DB
        text_values = resolve_source(text, data, "text")
        n = len(text_values)
        doc_ids = resolve_source(doc_id, data, "doc_id") if doc_id is not None else list(range(n))
        if len(doc_ids) != n:
            raise TypeError(f"`doc_id` has {len(doc_ids)} value(s), but `text` has {n}.")
        db.add_documents(self._session, doc_ids, text_values)
        self._session.commit()

        # First, add named arguments to the fields dict
        if prediction is not None:
            if not isinstance(prediction, LabelType):
                prediction = LabelType(prediction)
            fields["prediction"] = prediction
        if confidence is not None:
            if not isinstance(confidence, ScoreType):
                confidence = ScoreType(confidence)
            fields["confidence"] = confidence
        if gold_label is not None:
            if not isinstance(gold_label, LabelType):
                gold_label = LabelType(gold_label)
            fields["gold_label"] = gold_label
        if score is not None:
            if not isinstance(score, ScoreType):
                score = ScoreType(score)
            fields["score"] = score
        if embedding is not None:
            if not isinstance(embedding, Point2DType):
                embedding = Point2DType(embedding)
            fields["embedding"] = embedding
        if group is not None:
            if not isinstance(group, LabelType):
                group = LabelType(group)
            if group_definitions is not None:
                if group.definitions is not None:
                    raise TypeError(
                        "`group` already has a `definitions=` secondary; don't also pass `group_definitions=`."
                    )
                group = LabelType(group.source, definitions=group_definitions)
            fields["group"] = group
        elif group_definitions is not None:
            raise TypeError("`group_definitions` was given but no `group=` field was provided to attach it to.")

        # Now, populate the DB with all fields
        for field_name, source in fields.items():
            if not isinstance(source, _PrimaryType):
                raise TypeError(
                    f"`{field_name}` is given as raw input. Custom fields"
                    f"should be wrapped in an input type (LabelType, "
                    f"ScoreType, etc.) so that sourcetext knows how to "
                    f"deal with it datawise and in the UI."
                )

            values = source.resolve(data)
            if isinstance(source, LabelType):
                db.add_labels(self._session, field_name, doc_ids, values)
                if source.definitions:
                    db.add_label_definitions(self._session, field_name, source.definitions)
            elif isinstance(source, ScoreType):
                db.add_scores(self._session, field_name, doc_ids, values)
            elif isinstance(source, TextType):
                db.add_text(self._session, field_name, doc_ids, values)
            elif isinstance(source, TemporalType):
                granularity = source.granularity(data)
                if granularity == "year":
                    db.add_temporal_years(self._session, field_name, doc_ids, values)
                elif granularity == "day":
                    db.add_temporal_dates(self._session, field_name, doc_ids, values)
                else:
                    db.add_temporal_datetimes(self._session, field_name, doc_ids, values)
            elif isinstance(source, SpanType):
                db.add_spans(self._session, field_name, doc_ids, values)
            elif isinstance(source, Point2DType):
                db.add_points_2d(self._session, field_name, doc_ids, values)
            else:
                raise TypeError(f"Unsupported input type for `{field_name}`! Got {type(source)}")
            self._session.commit()

        self.doc_ids = doc_ids

        # Notes are matched back to documents by id only when the user chose the ids (`doc_id=`);
        # default ids are row positions, which change if the data is reordered.
        if notes_file is None and (Path.cwd() / DEFAULT_FILENAME).is_file():
            # The app's default notes file, from an earlier session: pick it up, so
            # those notes don't look lost when the same code runs again.
            notes_file = Path.cwd() / DEFAULT_FILENAME
            warnings.warn(
                f"Saving notes to {notes_file}, found in the working directory. "
                "Pass `notes_file=` to use another file.",
                stacklevel=2,
            )
        self._notes_file = NotesFile(notes_file, match_by="id" if doc_id is not None else "text")
        report = self._notes_file.load(self._session)
        self._session.commit()
        report.warn()

        self._server = None

    @staticmethod
    def _validate_mode(text: ColumnName | Iterable[str] | None, data: pd.DataFrame | None) -> None:
        if text is None:
            raise TypeError("`text` is required: a list of strings, or a column name (str) when `data=` is given.")
        if data is not None and not isinstance(text, str):
            raise TypeError(
                "When `data=` is given, `text` must be the name of the text column "
                f'(str), not a {type(text).__name__}. Pass text="<column name>".'
            )
        if data is None and isinstance(text, str):
            raise TypeError(
                "`text` looks like a column name (str), but no `data=` DataFrame was "
                "given to resolve it against. Pass `data=<DataFrame>`, or give `text` "
                "as a list of raw strings."
            )

    def start_server(self, port: int = 8001, block: bool | None = None):
        """Serve the visualizer application.

        Args:
            port: The port that the visualizer should be served on.
            block: If True, block until the server is stopped (e.g. via ctrl+c) —
                for a plain script. If False, run in the background within an
                already-running event loop (e.g. Jupyter). If None (default),
                auto-detect based on whether an event loop is already running.
        """

        self._server = BackgroundServer(self._create_session, self._notes_file, port=port)
        self._server.start(block=block)

    def stop_server(self):
        if self._server is not None:
            self._server.stop()
            self._server = None
