from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TypeAlias

import pandas as pd

import sourcetext.db as db
from sourcetext.server.backgroundserver import BackgroundServer
from sourcetext.types import (
    GroupType,
    IdType,
    IdValue,
    LabelType,
    LabelValue,
    Point2DType,
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
        texts: ColumnName | Iterable[str] = None,
        *,
        data: pd.DataFrame | None = None,
        ids: ColumnName | Iterable[IdValue] | IdType | None = None,
        predictions: ColumnName | Iterable[LabelValue] | LabelType | None = None,
        predictions_confidence: ColumnName | Iterable[ScoreValue] | ScoreType | None = None,
        gold_labels: ColumnName | Iterable[LabelValue] | LabelType | None = None,
        scores: ColumnName | Iterable[ScoreValue] | ScoreType | None = None,
        groups: ColumnName | Iterable[LabelValue] | LabelType | None = None,
        group_definitions: dict[str, Any] = None,
        **fields: LabelType | ScoreType | GroupType | TemporalType | Point2DType,
    ) -> None:
        self._validate_mode(texts, data)

        # Init DB
        self._create_session = db.get_sessionmaker()
        self._session = self._create_session()

        # resolve documents and add to DB
        text_values = resolve_source(texts, data, "texts")
        n = len(text_values)
        doc_ids = resolve_source(ids, data, "ids") if ids is not None else list(range(n))
        if len(doc_ids) != n:
            raise TypeError(f"`ids` has {len(doc_ids)} value(s), but `texts` has {n}.")
        db.add_documents(self._session, doc_ids, text_values)
        self._session.commit()

        # First, add named arguments to the fields dict
        if predictions is not None:
            if not isinstance(predictions, LabelType):
                predictions = LabelType(predictions)
            fields["predictions"] = predictions
        if predictions_confidence is not None:
            if not isinstance(predictions_confidence, ScoreType):
                predictions_confidence = ScoreType(predictions_confidence)
            fields["predictions_confidence"] = predictions_confidence
        if gold_labels is not None:
            if not isinstance(gold_labels, LabelType):
                gold_labels = LabelType(gold_labels)
            fields["gold_labels"] = gold_labels
        if scores is not None:
            if not isinstance(scores, ScoreType):
                scores = ScoreType(scores)
            fields["scores"] = scores
        if groups is not None:
            if not isinstance(groups, GroupType):
                groups = GroupType(groups)
            if group_definitions is not None:
                if groups.definitions is not None:
                    raise TypeError(
                        "`groups` already has a `definitions=` secondary; don't also pass `group_definitions=`."
                    )
                groups = GroupType(groups.source, definitions=group_definitions)
            fields["groups"] = groups
        elif group_definitions is not None:
            raise TypeError("`group_definitions` was given but no `groups=` field was provided to attach it to.")

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
            elif isinstance(source, ScoreType):
                db.add_scores(self._session, field_name, doc_ids, values)
            elif isinstance(source, GroupType):
                db.add_groups(self._session, field_name, doc_ids, values)
                if source.definitions:
                    db.add_group_definitions(self._session, field_name, source.definitions)
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

        self._server = None

    @staticmethod
    def _validate_mode(texts: ColumnName | Iterable[str] | None, data: pd.DataFrame | None) -> None:
        if texts is None:
            raise TypeError("`texts` is required: a list of strings, or a column name (str) when `data=` is given.")
        if data is not None and not isinstance(texts, str):
            raise TypeError(
                "When `data=` is given, `texts` must be the name of the text column "
                f'(str), not a {type(texts).__name__}. Pass texts="<column name>".'
            )
        if data is None and isinstance(texts, str):
            raise TypeError(
                "`texts` looks like a column name (str), but no `data=` DataFrame was "
                "given to resolve it against. Pass `data=<DataFrame>`, or give `texts` "
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

        self._server = BackgroundServer(self._create_session, port=port)
        self._server.start(block=block)

    def stop_server(self):
        if self._server is not None:
            self._server.stop()
            self._server = None
