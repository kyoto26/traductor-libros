import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DEFAULT_DB_PATH = DATA_DIR / "jobs.db"


def _get_db_path() -> Path:
    raw = os.environ.get("JOBS_DB_PATH")
    return Path(raw) if raw else _DEFAULT_DB_PATH


def get_connection() -> sqlite3.Connection:
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connection():
    # A fresh connection per operation, never shared across threads: the
    # background job thread and the /status, /download request threads all
    # hit the database independently, and reusing one sqlite3.Connection
    # across threads is a classic source of "database is locked" errors.
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id                TEXT PRIMARY KEY,
                format            TEXT NOT NULL,
                status            TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                input_path        TEXT NOT NULL,
                output_path       TEXT,
                total_blocks      INTEGER,
                translated_blocks INTEGER NOT NULL DEFAULT 0,
                error_message     TEXT,
                created_at        TEXT NOT NULL,
                updated_at        TEXT NOT NULL
            )
            """
        )
