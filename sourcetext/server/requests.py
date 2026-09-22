from typing import Any, Literal

from fastapi_camelcase import CamelModel


class FieldOut(CamelModel):
    name: str
    type: str
    values: list[Any] | None = None
    min: Any | None = None
    max: Any | None = None


class FieldFilterIn(CamelModel):
    field: str
    op: Literal["in", "range", "contains"]
    values: list[str] | None = None
    min: float | str | None = None
    max: float | str | None = None
    text: str | None = None


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


class ScatterPointOut(CamelModel):
    document_id: str
    x: float
    y: float
    text: str
    group: str | None = None


class ScatterResponse(CamelModel):
    fields: list[FieldOut]
    points: list[ScatterPointOut]
