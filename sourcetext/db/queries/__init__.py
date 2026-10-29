"""Read helpers, one module per concern (see the backend-organization skill). Re-exports
what code outside `db/` uses; the result dataclasses stay in their own modules."""

from sourcetext.db.queries.documents import count_documents, get_document, list_document_texts, list_documents
from sourcetext.db.queries.fields import list_fields, list_plot_fields, list_span_fields
from sourcetext.db.queries.filters import FieldFilter, Filter, SearchFilter
from sourcetext.db.queries.matrix import crosstab
from sourcetext.db.queries.notes import get_note, list_notes
from sourcetext.db.queries.plot import list_points_2d, list_score_pairs, list_strip_points
from sourcetext.db.queries.spans import list_document_spans, summarize_spans

__all__ = [
    "FieldFilter",
    "Filter",
    "SearchFilter",
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
