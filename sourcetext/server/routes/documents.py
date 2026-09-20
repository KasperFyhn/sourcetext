from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request

import sourcetext.db as db
from sourcetext.server.requests import DocumentsResponse, NoteIn

router = APIRouter(prefix="/api")


# Must stay `async def`: in-memory DuckDB only shares data within the thread that
# created the sessionmaker, and sync routes would run in FastAPI's threadpool.
@router.get("/documents", response_model=DocumentsResponse)
async def get_documents(request: Request, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    with request.app.state.db_sessionmaker() as session:
        return {
            "fields": [asdict(f) for f in db.list_fields(session)],
            "documents": [asdict(d) for d in db.list_documents(session, limit, offset)],
            "total": db.count_documents(session),
        }


@router.put("/documents/{document_id}/note", status_code=204)
async def put_note(document_id: str, note: NoteIn, request: Request) -> None:
    with request.app.state.db_sessionmaker() as session:
        try:
            db.set_note(session, document_id, note.text)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"No document with id {document_id!r}.")
        session.commit()
