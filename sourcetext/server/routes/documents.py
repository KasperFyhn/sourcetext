from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import TypeAdapter, ValidationError

import sourcetext.db as db
from sourcetext.server.requests import (
    CrosstabResponse,
    DocumentOut,
    DocumentSpansResponse,
    DocumentsResponse,
    FieldsResponse,
    FilterIn,
    NoteIn,
    NoteOut,
    ScatterResponse,
    SearchFilterIn,
    SpansResponse,
    StripResponse,
)

router = APIRouter(prefix="/api")

_filters_adapter = TypeAdapter(list[FilterIn])


def _parse_filters(filters: str | None) -> list[db.Filter] | None:
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
            "fields": _fields(request, session),
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
        fields = db.list_plot_fields(session)
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


@router.get("/documents/strip", response_model=StripResponse)
async def get_strip(
    request: Request,
    x_field: str = Query(alias="xField"),
    row_field: str = Query(alias="rowField"),
    color_field: str | None = Query(None, alias="colorField"),
    filters: str | None = Query(None),
):
    """One point per document along the score field `xField`, split into rows by the
    label field `rowField` and optionally colored by another (`colorField`):
    the plot view's strip plot, used when one of its axes is categorical."""
    with request.app.state.db_sessionmaker() as session:
        field_filters = _parse_filters(filters)
        try:
            points = db.list_strip_points(
                session, x_field, row_field=row_field, color_field=color_field, filters=field_filters
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"points": [asdict(p) for p in points]}


@router.get("/documents/crosstab", response_model=CrosstabResponse)
async def get_crosstab(
    request: Request,
    row_field: str = Query(alias="rowField"),
    col_field: str = Query(alias="colField"),
):
    """Document counts per value pair of two label fields (a confusion
    matrix, for e.g. gold labels vs. predictions)."""
    with request.app.state.db_sessionmaker() as session:
        try:
            cells = db.crosstab(session, row_field, col_field)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"cells": [asdict(c) for c in cells]}


@router.get("/documents/fields", response_model=FieldsResponse)
async def get_fields(request: Request):
    """The full field list (all typed-field kinds), for a document-detail pane that
    isn't otherwise loading a page of documents (e.g. the scatter view)."""
    with request.app.state.db_sessionmaker() as session:
        return {"fields": _fields(request, session)}


@router.get("/spans", response_model=SpansResponse)
async def get_spans(
    request: Request,
    field: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    filters: str | None = Query(None),
):
    """An overview of the span field `field` (default: the first one) for the span
    view: counts per label, and the most frequent span types. A "span" filter on
    `field` in `filters` narrows which spans are counted; filters on other fields
    narrow which documents. Its documents come from the tabular route with the same
    filters."""
    with request.app.state.db_sessionmaker() as session:
        field_filters = _parse_filters(filters)
        fields = db.list_span_fields(session)
        if field is None and fields:
            field = fields[0]
        if field is None:
            return {"fields": [], "field": None, "labels": [], "types": [], "total_types": 0}
        try:
            summary = db.summarize_spans(session, field, limit=limit, filters=field_filters)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"fields": fields, "field": field, **asdict(summary)}


# Registered after the static `/documents/tabular`, `/documents/scatter`, `/documents/strip`,
# `/documents/crosstab` and `/documents/fields` routes above: FastAPI matches routes in
# registration order, so those literal paths are matched before falling through to this
# `{document_id}` route.
@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, request: Request):
    with request.app.state.db_sessionmaker() as session:
        document = db.get_document(session, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail=f"No document with id {document_id!r}.")
        return asdict(document)


@router.get("/documents/{document_id}/note")
async def get_note(document_id: str, request: Request) -> NoteOut:
    with request.app.state.db_sessionmaker() as session:
        try:
            return NoteOut(text=db.get_note(session, document_id))
        except KeyError:
            raise HTTPException(status_code=404, detail=f"No document with id {document_id!r}.")


@router.put("/documents/{document_id}/note", status_code=204)
async def put_note(document_id: str, note: NoteIn, request: Request) -> None:
    notes_file = request.app.state.notes_file
    if notes_file.path is None:
        raise HTTPException(status_code=409, detail="Choose a notes file before writing notes.")
    with request.app.state.db_sessionmaker() as session:
        try:
            db.set_note(session, document_id, note.text)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"No document with id {document_id!r}.")
        # Written to the file before committing, so a note that couldn't be saved
        # to the file isn't kept in memory either.
        try:
            notes_file.save(session)
        except OSError as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Could not write {notes_file.path}: {e}")
        session.commit()


@router.get("/documents/{document_id}/spans", response_model=DocumentSpansResponse)
async def get_document_spans(document_id: str, request: Request, filters: str | None = Query(None)):
    """Every span on one document, across all span fields, in text order. "span"
    filters in `filters` prune their field's spans; other filters are ignored."""
    with request.app.state.db_sessionmaker() as session:
        field_filters = _parse_filters(filters)
        try:
            spans = db.list_document_spans(session, document_id, filters=field_filters)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"No document with id {document_id!r}.")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"spans": [asdict(s) for s in spans]}
