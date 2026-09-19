from fastapi import APIRouter, Request
from sqlalchemy import func, select

import sourcetext.db as db
from sourcetext.db.schema import Document
from sourcetext.server.requests import PingResponse

router = APIRouter(prefix="/api")


# Must stay `async def`: in-memory DuckDB only shares data within the thread that
# created the sessionmaker, and sync routes would run in FastAPI's threadpool.
@router.get("/ping", response_model=PingResponse)
async def ping(request: Request) -> PingResponse:
    """Dummy round trip: write a document, then read the document count back."""
    with request.app.state.db_sessionmaker() as session:
        count = session.execute(select(func.count()).select_from(Document)).scalar_one()
        db.add_documents(session, [f"ping-{count}"], ["Dummy document from /api/ping"])
        session.commit()
        count = session.execute(select(func.count()).select_from(Document)).scalar_one()
    return PingResponse(message="Frontend, API and DB are connected.", document_count=count)
