from typing import Any

from fastapi_camelcase import CamelModel


class FieldOut(CamelModel):
    name: str
    type: str


class DocumentOut(CamelModel):
    id: str
    text: str
    values: dict[str, Any]
    note: str


class DocumentsResponse(CamelModel):
    fields: list[FieldOut]
    documents: list[DocumentOut]
    total: int


class NoteIn(CamelModel):
    text: str
