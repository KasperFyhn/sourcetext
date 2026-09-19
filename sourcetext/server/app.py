from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sourcetext.db import get_sessionmaker
from sourcetext.server.routes.ping import router as ping_router

build_directory = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app_arg: FastAPI):
    if getattr(app_arg.state, "db_sessionmaker", None) is None:
        raise ValueError("No DB sessionmaker provided. Set `app.state.db_sessionmaker` before startup.")

    if not (build_directory / "index.html").is_file():
        raise ValueError(f"No frontend build found in '{build_directory}'. Run ./scripts/build-frontend.sh first.")
    # Mounted last so that API routes registered on the app take precedence.
    app_arg.mount("", StaticFiles(directory=build_directory, html=True), name="static")

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

app.include_router(ping_router)


if __name__ == "__main__":
    import uvicorn

    app.state.db_sessionmaker = get_sessionmaker()
    uvicorn.run(app, host="localhost", port=8001)
