from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import TypeAdapter, ValidationError

import sourcetext.db as db
from sourcetext.server.requests import (
    DocumentOut,
    DocumentsResponse,
    FieldFilterIn,
    FieldsResponse,
    NoteIn,
    ScatterResponse,
)

router = APIRouter(prefix="/api")

_field_filters_adapter = TypeAdapter(list[FieldFilterIn])


def _parse_filters(filters: str | None) -> list[db.FieldFilter] | None:
    """Decode the `filters` query param (a JSON-encoded array — see FieldFilterIn)
    into `db.FieldFilter`s, or raise a 400 if it's malformed."""
    if filters is None:
        return None
    try:
        parsed = _field_filters_adapter.validate_json(filters)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [db.FieldFilter(**f.model_dump()) for f in parsed]


# Must stay `async def`: in-memory DuckDB only shares data within the thread that
# created the sessionmaker, and sync routes would run in FastAPI's threadpool.
@router.get("/documents/tabular", response_model=DocumentsResponse)
async def get_tabular_documents(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_field: str | None = Query(None, alias="sortField"),
    sort_dir: str = Query("asc", alias="sortDir", pattern="^(asc|desc)$"),
    filters: str | None = Query(None),
):
    with request.app.state.db_sessionmaker() as session:
        field_filters = _parse_filters(filters)
        try:
            documents = db.list_documents(
                session,
                limit,
                offset,
                sort_field=sort_field,
                sort_desc=sort_dir == "desc",
                filters=field_filters,
            )
            total = db.count_documents(session, filters=field_filters)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {
            "fields": [asdict(f) for f in db.list_fields(session)],
            "documents": [asdict(d) for d in documents],
            "total": total,
        }


@router.get("/documents/scatter", response_model=ScatterResponse)
async def get_scatter(
    request: Request,
    field: str | None = Query(None),
    x_field: str | None = Query(None, alias="xField"),
    y_field: str | None = Query(None, alias="yField"),
    color_field: str | None = Query(None, alias="colorField"),
    filters: str | None = Query(None),
):
    if field is not None and (x_field is not None or y_field is not None):
        raise HTTPException(status_code=400, detail="Provide either `field` or `xField`+`yField`, not both.")
    if (x_field is None) != (y_field is None):
        raise HTTPException(status_code=400, detail="`xField` and `yField` must be provided together.")

    with request.app.state.db_sessionmaker() as session:
        field_filters = _parse_filters(filters)
        fields = db.list_scatter_fields(session)
        try:
            if field is not None:
                points = db.list_points_2d(session, field, group_field=color_field, filters=field_filters)
            elif x_field is not None:
                points = db.list_score_pairs(session, x_field, y_field, group_field=color_field, filters=field_filters)
            else:
                points = []
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {
            "fields": [asdict(f) for f in fields],
            "points": [asdict(p) for p in points],
        }


@router.get("/documents/fields", response_model=FieldsResponse)
async def get_fields(request: Request):
    """The full field list (all typed-field kinds), for a document-detail pane that
    isn't otherwise loading a page of documents (e.g. the scatter view)."""
    with request.app.state.db_sessionmaker() as session:
        return {"fields": [asdict(f) for f in db.list_fields(session)]}


# Registered after the static `/documents/tabular`, `/documents/scatter` and
# `/documents/fields` routes above: FastAPI matches routes in registration order, so
# those literal paths are matched before falling through to this `{document_id}` route.
@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, request: Request):
    with request.app.state.db_sessionmaker() as session:
        document = db.get_document(session, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail=f"No document with id {document_id!r}.")
        return asdict(document)


@router.put("/documents/{document_id}/note", status_code=204)
async def put_note(document_id: str, note: NoteIn, request: Request) -> None:
    with request.app.state.db_sessionmaker() as session:
        try:
            db.set_note(session, document_id, note.text)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"No document with id {document_id!r}.")
        session.commit()
