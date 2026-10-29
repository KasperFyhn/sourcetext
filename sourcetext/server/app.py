import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sourcetext.notes import NotesFile
from sourcetext.server.routes.documents import router as documents_router
from sourcetext.server.routes.matrix import router as matrix_router
from sourcetext.server.routes.notes import router as notes_router
from sourcetext.server.routes.plot import router as plot_router
from sourcetext.server.routes.spans import router as spans_router

build_directory = Path(__file__).parent / "static"

# Dev-only switch, not public API: dev tooling sets `sourcetext.server.app._dev = True` before
# starting the server to skip mounting the built UI (the Vite dev server serves it instead).
_dev = False


@asynccontextmanager
async def lifespan(app_arg: FastAPI):
    if getattr(app_arg.state, "db_sessionmaker", None) is None:
        raise ValueError("No DB sessionmaker provided. Set `app.state.db_sessionmaker` before startup.")
    if getattr(app_arg.state, "notes_file", None) is None:
        app_arg.state.notes_file = NotesFile()

    if _dev:
        logging.info("Dev mode: serving the API only, not mounting the built UI.")
    elif (build_directory / "index.html").is_file():
        # Mounted last so that API routes registered on the app take precedence.
        app_arg.mount("", StaticFiles(directory=build_directory, html=True), name="static")
    else:
        raise ValueError(
            f"No frontend build found in '{build_directory}'. Run ./scripts/build-frontend.sh to create one."
        )

    yield


app = FastAPI(lifespan=lifespan)

# noinspection PyTypeChecker
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # specify specific origins if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The documents router goes last: FastAPI matches routes in registration order, so the
# literal `/documents/scatter`, `/documents/strip` and `/documents/crosstab` paths must be
# registered before its `/documents/{document_id}` route.
app.include_router(plot_router)
app.include_router(matrix_router)
app.include_router(spans_router)
app.include_router(notes_router)
app.include_router(documents_router)
