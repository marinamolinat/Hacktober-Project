"""Snowflake access (SQLite fallback for local dev). All calls are serialized
through one lock, which is the v1 "serialized write dispatcher" (specs.md §2.4)."""
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

SCHEMA_FILE = Path(__file__).parent / "snowflake" / "002_schema.sql"

_lock = threading.RLock()
_conn = None
_in_tx = False


class DatabaseUnavailable(Exception):
    pass


def using_snowflake():
    return bool(os.getenv("SNOWFLAKE_ACCOUNT"))


def _connect():
    if using_snowflake():
        import snowflake.connector

        return snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            role=os.getenv("SNOWFLAKE_ROLE") or None,
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "HACKATHON_APP_WH"),
            database=os.getenv("SNOWFLAKE_DATABASE", "HACKATHON_DB"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "APP"),
            session_parameters={"TIMEZONE": "UTC", "STATEMENT_TIMEOUT_IN_SECONDS": 60},
            client_session_keep_alive=True,
            autocommit=True,
        )
    conn = sqlite3.connect(os.getenv("SQLITE_PATH", "local.db"), check_same_thread=False)
    conn.create_function("PARSE_JSON", 1, lambda s: s)
    conn.create_function("TO_ARRAY", 1, lambda s: s)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _get():
    global _conn
    if _conn is None:
        try:
            _conn = _connect()
        except Exception as e:
            raise DatabaseUnavailable(str(e)) from e
    return _conn


def query(sql, params=()):
    """Run one statement with %s placeholders; returns rows as dicts with lowercase keys."""
    with _lock:
        conn = _get()
        cur = conn.cursor()
        cur.execute(sql if using_snowflake() else sql.replace("%s", "?"), params)
        rows = []
        if cur.description:
            cols = [d[0].lower() for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        if not using_snowflake() and not _in_tx:
            conn.commit()
        return rows


def one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None


@contextmanager
def transaction():
    global _in_tx
    with _lock:
        conn = _get()
        if using_snowflake():
            conn.cursor().execute("BEGIN")
        _in_tx = True
        try:
            yield
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            _in_tx = False


def _to_sqlite(stmt):
    stmt = re.sub(r"VARCHAR\(\d+\)|TIMESTAMP_TZ|VARIANT|\bARRAY\b|\bDATE\b", "TEXT", stmt)
    stmt = re.sub(r"NUMBER\(\d+,\s*[1-9]\)|FLOAT", "REAL", stmt)
    return re.sub(r"NUMBER\(\d+,\s*0\)|BOOLEAN", "INTEGER", stmt)


def init_schema():
    sql = re.sub(r"--[^\n]*", "", SCHEMA_FILE.read_text())
    for stmt in filter(None, (s.strip() for s in sql.split(";"))):
        query(stmt if using_snowflake() else _to_sqlite(stmt))
