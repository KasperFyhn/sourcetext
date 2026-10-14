from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from sourcetext.notes import DEFAULT_FILENAME, NotesFile
from sourcetext.server.requests import NotesFileIn, NotesFileLoadOut, NotesFileOut

router = APIRouter(prefix="/api/notes")


def _status(notes_file: NotesFile, load: NotesFileLoadOut | None = None) -> NotesFileOut:
    return NotesFileOut(
        path=str(notes_file.path) if notes_file.path is not None else None,
        suggested_path=str(Path.cwd() / DEFAULT_FILENAME),
        load=load,
    )


@router.get("/file")
async def get_notes_file(request: Request) -> NotesFileOut:
    return _status(request.app.state.notes_file)


@router.put("/file")
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
