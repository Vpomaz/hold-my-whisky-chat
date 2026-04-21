import sqlite3
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_st():
    st = MagicMock()
    st.secrets = {"app": {"db_path": ":memory:"}}
    st.cache_resource.side_effect = lambda f: f  # passthrough decorator
    with patch.dict("sys.modules", {"streamlit": st}):
        yield st


def test_apply_schema_creates_core_tables(mock_st):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from importlib import reload
    import utils.db as db_module
    reload(db_module)
    db_module._apply_schema(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for expected in ("users", "rooms", "messages", "attachments", "user_sessions", "friendships"):
        assert expected in tables, f"Missing table: {expected}"


def test_apply_schema_adds_data_column_when_missing(mock_st):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Create attachments without 'data' column to trigger migration path
    conn.execute(
        "CREATE TABLE attachments ("
        "id INTEGER PRIMARY KEY, message_id INTEGER, original_name TEXT, "
        "stored_path TEXT NOT NULL DEFAULT '', mime_type TEXT, "
        "file_size INTEGER NOT NULL DEFAULT 0, comment TEXT, created_at TEXT)"
    )
    from importlib import reload
    import utils.db as db_module
    reload(db_module)
    db_module._apply_schema(conn)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(attachments)").fetchall()]
    assert "data" in cols


def test_apply_schema_migration_idempotent(mock_st):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from importlib import reload
    import utils.db as db_module
    reload(db_module)
    db_module._apply_schema(conn)
    # Second call must not raise (data column already exists → ALTER caught silently)
    db_module._apply_schema(conn)


def test_get_db_returns_connection(mock_st):
    from importlib import reload
    import utils.db as db_module
    reload(db_module)
    conn = db_module.get_db()
    result = conn.execute("SELECT 1 AS val").fetchone()
    assert result["val"] == 1
    conn.close()
