import sqlite3
import streamlit as st


@st.cache_resource
def get_db() -> sqlite3.Connection:
    db_path = st.secrets["app"]["db_path"]
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    _apply_schema(conn)
    return conn


def _apply_schema(conn: sqlite3.Connection) -> None:
    with open("sql/init_schema.sql") as f:
        conn.executescript(f.read())
    # Migration: add base64 data column to attachments for existing databases
    try:
        conn.execute("ALTER TABLE attachments ADD COLUMN data TEXT")
        conn.commit()
    except Exception:
        pass
