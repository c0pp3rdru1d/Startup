from __future__ import annotations

from contextlib import contextmanager
from sqlmodel import SQLModel, Session, create_engine
import sqlite3

DB_PATH = "sentineldesk.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def _col_exists(cur: sqlite3.Cursor, table: str, col: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    return col in cols


def _ensure_columns() -> None:
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()

        # Hosts
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='host'")
        if cur.fetchone():
            if not _col_exists(cur, "host", "tcp_ports"):
                cur.execute("ALTER TABLE host ADD COLUMN tcp_ports TEXT DEFAULT ''")

        # CheckResult
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='checkresult'")
        if cur.fetchone():
            if not _col_exists(cur, "checkresult", "check_type"):
                cur.execute("ALTER TABLE checkresult ADD COLUMN check_type TEXT DEFAULT 'ping'")
            if not _col_exists(cur, "checkresult", "target"):
                cur.execute("ALTER TABLE checkresult ADD COLUMN target TEXT DEFAULT ''")

        con.commit()
    finally:
        con.close()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _ensure_columns()


@contextmanager
def get_session() -> Session:
    with Session(engine) as session:
        yield session

