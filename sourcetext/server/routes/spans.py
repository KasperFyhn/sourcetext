from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request

import sourcetext.db as db
from sourcetext.server.requests import DocumentSpansResponse, SpansResponse, parse_filters

router = APIRouter(prefix="/api")


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
        field_filters = parse_filters(filters)
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


@router.get("/documents/{document_id}/spans", response_model=DocumentSpansResponse)
async def get_document_spans(document_id: str, request: Request, filters: str | None = Query(None)):
    """Every span on one document, across all span fields, in text order. "span"
    filters in `filters` prune their field's spans; other filters are ignored."""
    with request.app.state.db_sessionmaker() as session:
        field_filters = parse_filters(filters)
        try:
            spans = db.list_document_spans(session, document_id, filters=field_filters)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"No document with id {document_id!r}.")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"spans": [asdict(s) for s in spans]}
