from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request

import sourcetext.db as db
from sourcetext.server.requests import ScatterResponse, StripResponse, parse_filters

router = APIRouter(prefix="/api")


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
        field_filters = parse_filters(filters)
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
        field_filters = parse_filters(filters)
        try:
            points = db.list_strip_points(
                session, x_field, row_field=row_field, color_field=color_field, filters=field_filters
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"points": [asdict(p) for p in points]}
