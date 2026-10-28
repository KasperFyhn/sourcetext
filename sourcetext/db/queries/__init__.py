"""Read helpers, one module per concern (see the backend-organization skill)."""

from sourcetext.db.queries.documents import (
    DocumentRow,
    count_documents,
    get_document,
    list_document_texts,
    list_documents,
)
from sourcetext.db.queries.fields import FieldInfo, list_fields, list_plot_fields, list_span_fields
from sourcetext.db.queries.filters import FieldFilter, Filter, SearchFilter
from sourcetext.db.queries.matrix import CrosstabCell, crosstab
from sourcetext.db.queries.notes import NoteRow, get_note, list_notes
from sourcetext.db.queries.plot import (
    ScatterPointRow,
    StripPointRow,
    list_points_2d,
    list_score_pairs,
    list_strip_points,
)
from sourcetext.db.queries.spans import (
    SpanLabelRow,
    SpanRow,
    SpanSummary,
    SpanTypeRow,
    list_document_spans,
    summarize_spans,
)

__all__ = [
    "CrosstabCell",
    "DocumentRow",
    "FieldFilter",
    "FieldInfo",
    "Filter",
    "NoteRow",
    "ScatterPointRow",
    "SearchFilter",
    "SpanLabelRow",
    "SpanRow",
    "SpanSummary",
    "SpanTypeRow",
    "StripPointRow",
    "count_documents",
    "crosstab",
    "get_document",
    "get_note",
    "list_document_spans",
    "list_document_texts",
    "list_documents",
    "list_fields",
    "list_notes",
    "list_plot_fields",
    "list_points_2d",
    "list_score_pairs",
    "list_span_fields",
    "list_strip_points",
    "summarize_spans",
]
