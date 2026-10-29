from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

import sourcetext.db as db
from sourcetext.notes import DEFAULT_FILENAME, NotesFile
from sourcetext.server.requests import NoteIn, NoteOut, NotesFileIn, NotesFileLoadOut, NotesFileOut

router = APIRouter(prefix="/api")


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


def _status(notes_file: NotesFile, load: NotesFileLoadOut | None = None) -> NotesFileOut:
    return NotesFileOut(
        path=str(notes_file.path) if notes_file.path is not None else None,
        suggested_path=str(Path.cwd() / DEFAULT_FILENAME),
        load=load,
    )


@router.get("/notes/file")
async def get_notes_file(request: Request) -> NotesFileOut:
    return _status(request.app.state.notes_file)


@router.put("/notes/file")
async def put_notes_file(body: NotesFileIn, request: Request) -> NotesFileOut:
    """Choose the file to save notes to (relative paths resolve against the Python
    process's working directory), merging in any notes it already holds. Until one
    is chosen, notes can't be written."""
    notes_file: NotesFile = request.app.state.notes_file
    if not body.path.strip():
        raise HTTPException(status_code=400, detail="The path is empty.")
    with request.app.state.db_sessionmaker() as session:
        try:
            report = notes_file.set_path(body.path.strip(), session)
        except (OSError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        session.commit()
    return _status(notes_file, NotesFileLoadOut(loaded=report.loaded, messages=report.messages()))
