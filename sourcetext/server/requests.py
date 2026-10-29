from typing import Annotated, Any, Literal

from fastapi import HTTPException
from fastapi_camelcase import CamelModel
from pydantic import Field, TypeAdapter, ValidationError

import sourcetext.db as db


class FieldOut(CamelModel):
    name: str
    type: str
    values: list[Any] | None = None
    min: Any | None = None
    max: Any | None = None
    definitions: dict[str, Any] | None = None


class FieldFilterIn(CamelModel):
    field: str
    op: Literal["in", "range", "span"]
    values: list[str | None] | None = None
    min: float | str | None = None
    max: float | str | None = None
    text: str | None = None
    type_text: str | None = None


class SearchFilterIn(CamelModel):
    op: Literal["search"]
    text: str
    fields: list[str]


FilterIn = Annotated[FieldFilterIn | SearchFilterIn, Field(discriminator="op")]

_filters_adapter = TypeAdapter(list[FilterIn])


def parse_filters(filters: str | None) -> list[db.Filter] | None:
    """Decode the `filters` query param (a JSON-encoded array — see FilterIn) into
    `db.FieldFilter`s and `db.SearchFilter`s, or raise a 400 if it's malformed."""
    if filters is None:
        return None
    try:
        parsed = _filters_adapter.validate_json(filters)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [
        db.SearchFilter(f.text, f.fields) if isinstance(f, SearchFilterIn) else db.FieldFilter(**f.model_dump())
        for f in parsed
    ]


class DocumentOut(CamelModel):
    id: str
    text: str
    values: dict[str, Any]
    note: str


class DocumentsResponse(CamelModel):
    fields: list[FieldOut]
    documents: list[DocumentOut]
    total: int


class FieldsResponse(CamelModel):
    fields: list[FieldOut]


class NoteIn(CamelModel):
    text: str


class NoteOut(CamelModel):
    text: str


class NotesFileIn(CamelModel):
    path: str


class NotesFileLoadOut(CamelModel):
    loaded: int
    messages: list[str]


class NotesFileOut(CamelModel):
    path: str | None
    suggested_path: str
    # Set when a file was just chosen: what loading its existing notes found.
    load: NotesFileLoadOut | None = None


class ScatterPointOut(CamelModel):
    document_id: str
    x: float
    y: float
    text: str
    group: str | None = None


class ScatterResponse(CamelModel):
    fields: list[FieldOut]
    points: list[ScatterPointOut]


class StripPointOut(CamelModel):
    document_id: str
    x: float
    text: str
    row: str | None = None
    color: str | None = None


class StripResponse(CamelModel):
    points: list[StripPointOut]


class CrosstabCellOut(CamelModel):
    row: str | None
    col: str | None
    count: int


class CrosstabResponse(CamelModel):
    cells: list[CrosstabCellOut]


class SpanLabelOut(CamelModel):
    label: str | None
    spans: int
    documents: int


class SpanTypeOut(CamelModel):
    text: str
    label: str | None
    spans: int
    documents: int
    variants: int


class SpansResponse(CamelModel):
    # Every span field, and the one summarized (None if there are no span fields).
    fields: list[str]
    field: str | None
    labels: list[SpanLabelOut]
    types: list[SpanTypeOut]
    total_types: int


class DocumentSpanOut(CamelModel):
    field: str
    start: int
    end: int
    text: str
    norm_text: str | None
    label: str | None
    score: float | None


class DocumentSpansResponse(CamelModel):
    spans: list[DocumentSpanOut]
