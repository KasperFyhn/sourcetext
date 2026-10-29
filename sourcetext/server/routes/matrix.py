from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request

import sourcetext.db as db
from sourcetext.server.requests import CrosstabResponse

router = APIRouter(prefix="/api")


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
