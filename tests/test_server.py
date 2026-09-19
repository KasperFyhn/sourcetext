from fastapi.testclient import TestClient

from sourcetext.db import get_sessionmaker
from sourcetext.server.app import app


def test_ping_writes_and_reads_from_db(tmp_path):
    # File-backed: TestClient runs the app in another thread, and in-memory DuckDB isn't shared across threads.
    app.state.db_sessionmaker = get_sessionmaker(f"duckdb:///{tmp_path / 'test.duckdb'}")
    # Not used as a context manager, so the lifespan (static build check) is skipped.
    client = TestClient(app)

    first = client.get("/api/ping")
    second = client.get("/api/ping")

    assert first.status_code == 200
    assert first.json()["documentCount"] == 1
    assert second.json()["documentCount"] == 2
