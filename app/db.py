from __future__ import annotations

from contextlib import contextmanager
from sqlmodel import SQLModel, Session, create_engine

DB_PATH = "sentineldesk.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Session:
    with Session(engine) as session:
        yield session

