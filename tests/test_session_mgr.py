import sqlite3
import pytest
from services.session_mgr import create_session, get_sessions, delete_session, update_presence


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    with open("sql/init_schema.sql") as f:
        c.executescript(f.read())
    c.execute("INSERT INTO users (id, email, username, password_hash) VALUES (1,'a@x.com','alice','x')")
    c.execute("INSERT INTO users (id, email, username, password_hash) VALUES (2,'b@x.com','bob','x')")
    c.commit()
    yield c
    c.close()


# ── create_session ────────────────────────────────────────────────────────────

def test_create_session_returns_string(conn):
    sid = create_session(conn, 1)
    assert isinstance(sid, str)
    assert len(sid) == 36  # UUID format


def test_create_session_stores_row(conn):
    sid = create_session(conn, 1)
    row = conn.execute("SELECT * FROM user_sessions WHERE id=?", (sid,)).fetchone()
    assert row is not None
    assert row["user_id"] == 1
    assert row["presence"] == "online"


def test_create_session_with_agent_and_ip(conn):
    sid = create_session(conn, 1, user_agent="Mozilla/5.0", ip_address="127.0.0.1")
    row = conn.execute("SELECT user_agent, ip_address FROM user_sessions WHERE id=?", (sid,)).fetchone()
    assert row["user_agent"] == "Mozilla/5.0"
    assert row["ip_address"] == "127.0.0.1"


def test_create_session_default_empty_strings(conn):
    sid = create_session(conn, 1)
    row = conn.execute("SELECT user_agent, ip_address FROM user_sessions WHERE id=?", (sid,)).fetchone()
    assert row["user_agent"] == ""
    assert row["ip_address"] == ""


def test_create_session_unique_ids(conn):
    sid1 = create_session(conn, 1)
    sid2 = create_session(conn, 1)
    assert sid1 != sid2


# ── get_sessions ──────────────────────────────────────────────────────────────

def test_get_sessions_returns_user_sessions(conn):
    create_session(conn, 1)
    create_session(conn, 1)
    sessions = get_sessions(conn, 1)
    assert len(sessions) == 2


def test_get_sessions_empty(conn):
    assert get_sessions(conn, 1) == []


def test_get_sessions_only_for_user(conn):
    create_session(conn, 1)
    create_session(conn, 2)
    # only user 1's session returned; user 2's is excluded
    assert len(get_sessions(conn, 1)) == 1
    assert len(get_sessions(conn, 2)) == 1


def test_get_sessions_fields(conn):
    create_session(conn, 1, "Firefox", "10.0.0.1")
    s = get_sessions(conn, 1)[0]
    assert "id" in s.keys()
    assert "user_agent" in s.keys()
    assert "last_seen" in s.keys()
    assert "presence" in s.keys()


# ── delete_session ────────────────────────────────────────────────────────────

def test_delete_session_removes_row(conn):
    sid = create_session(conn, 1)
    delete_session(conn, sid)
    row = conn.execute("SELECT 1 FROM user_sessions WHERE id=?", (sid,)).fetchone()
    assert row is None


def test_delete_session_nonexistent_noop(conn):
    delete_session(conn, "nonexistent-uuid")  # should not raise


def test_delete_session_only_removes_target(conn):
    sid1 = create_session(conn, 1)
    sid2 = create_session(conn, 1)
    delete_session(conn, sid1)
    remaining = get_sessions(conn, 1)
    assert len(remaining) == 1
    assert remaining[0]["id"] == sid2


# ── update_presence ───────────────────────────────────────────────────────────

def test_update_presence_changes_status(conn):
    sid = create_session(conn, 1)
    update_presence(conn, sid, "afk")
    row = conn.execute("SELECT presence FROM user_sessions WHERE id=?", (sid,)).fetchone()
    assert row["presence"] == "afk"


def test_update_presence_to_offline(conn):
    sid = create_session(conn, 1)
    update_presence(conn, sid, "offline")
    row = conn.execute("SELECT presence FROM user_sessions WHERE id=?", (sid,)).fetchone()
    assert row["presence"] == "offline"


def test_update_presence_updates_last_seen(conn):
    sid = create_session(conn, 1)
    original = conn.execute("SELECT last_seen FROM user_sessions WHERE id=?", (sid,)).fetchone()["last_seen"]
    update_presence(conn, sid, "online")
    updated = conn.execute("SELECT last_seen FROM user_sessions WHERE id=?", (sid,)).fetchone()["last_seen"]
    assert updated >= original
