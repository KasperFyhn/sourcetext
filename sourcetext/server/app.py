import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sourcetext.server.routes.documents import router as documents_router

build_directory = Path(__file__).parent / "static"

# Dev-only switch, not public API: dev tooling sets `sourcetext.server.app.DEV = True` before
# starting the server to skip mounting the built UI (the Vite dev server serves it instead).
_dev = False


@asynccontextmanager
async def lifespan(app_arg: FastAPI):
    if getattr(app_arg.state, "db_sessionmaker", None) is None:
        raise ValueError("No DB sessionmaker provided. Set `app.state.db_sessionmaker` before startup.")

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

app.include_router(documents_router)
