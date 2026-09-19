from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from sourcetext.db.schema import Base


def get_sessionmaker(url: str = "duckdb:///:memory:") -> sessionmaker[Session]:
    """Build a sessionmaker bound to `url`, creating tables if they don't exist yet.

    Defaults to an in-memory DuckDB engine per sourcetext-spec.md's backend choice.
    """
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
