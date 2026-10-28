from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request

import sourcetext.db as db
from sourcetext.server.requests import DocumentOut, DocumentsResponse, FieldsResponse, parse_filters

router = APIRouter(prefix="/api")


def _fields(request: Request, session) -> list[dict]:
    """The full field list with its filter metadata (`db.list_fields`), computed
    once per DB: typed fields never change after `SourceText` is built, and the
    metadata scans every value. Keyed by the sessionmaker, so a new DB (e.g. in
    tests) isn't served a stale list."""
    sessionmaker = request.app.state.db_sessionmaker
    cached = getattr(request.app.state, "fields_cache", None)
    if cached is None or cached[0] is not sessionmaker:
        cached = (sessionmaker, [asdict(f) for f in db.list_fields(session)])
        request.app.state.fields_cache = cached
    return cached[1]


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
        field_filters = parse_filters(filters)
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
            "fields": _fields(request, session),
            "documents": [asdict(d) for d in documents],
            "total": total,
        }


@router.get("/documents/fields", response_model=FieldsResponse)
async def get_fields(request: Request):
    """The full field list (all typed-field kinds), for a document-detail pane that
    isn't otherwise loading a page of documents (e.g. the scatter view)."""
    with request.app.state.db_sessionmaker() as session:
        return {"fields": _fields(request, session)}


# Registered after the static `/documents/tabular` and `/documents/fields` routes above,
# and this router after the plot and matrix routers (see `app.py`): FastAPI matches
# routes in registration order, so those literal paths are matched before falling
# through to this `{document_id}` route.
@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, request: Request):
    with request.app.state.db_sessionmaker() as session:
        document = db.get_document(session, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail=f"No document with id {document_id!r}.")
        return asdict(document)
