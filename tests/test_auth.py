import sqlite3
import pytest
from services.auth import (
    register_user, authenticate, hash_password, verify_password,
    update_email, change_password, delete_account,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    with open("sql/init_schema.sql") as f:
        c.executescript(f.read())
    yield c
    c.close()


def test_hash_and_verify():
    h = hash_password("secret")
    assert verify_password("secret", h)
    assert not verify_password("wrong", h)


def test_register_and_authenticate(conn):
    register_user(conn, "u@example.com", "user1", "pass123")
    result = authenticate(conn, "u@example.com", "pass123")
    assert result is not None
    assert result["username"] == "user1"


def test_wrong_password(conn):
    register_user(conn, "u@example.com", "user1", "pass123")
    assert authenticate(conn, "u@example.com", "wrong") is None


# ── update_email ──────────────────────────────────────────────────────────────

def _uid(conn, username):
    return conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()["id"]


def test_update_email_success(conn):
    register_user(conn, "old@example.com", "user1", "pass")
    ok, msg = update_email(conn, _uid(conn, "user1"), "new@example.com")
    assert ok is True
    row = conn.execute("SELECT email FROM users WHERE username='user1'").fetchone()
    assert row["email"] == "new@example.com"


def test_update_email_duplicate_returns_error(conn):
    register_user(conn, "a@example.com", "user1", "pass")
    register_user(conn, "b@example.com", "user2", "pass")
    ok, msg = update_email(conn, _uid(conn, "user1"), "b@example.com")
    assert ok is False
    assert "taken" in msg.lower()


# ── change_password ───────────────────────────────────────────────────────────

def test_change_password_success(conn):
    register_user(conn, "a@example.com", "user1", "oldpass")
    ok, _ = change_password(conn, _uid(conn, "user1"), "oldpass", "newpass")
    assert ok is True
    assert authenticate(conn, "a@example.com", "newpass") is not None


def test_change_password_wrong_old(conn):
    register_user(conn, "a@example.com", "user1", "oldpass")
    ok, msg = change_password(conn, _uid(conn, "user1"), "wrongpass", "newpass")
    assert ok is False
    assert "incorrect" in msg.lower()


def test_change_password_user_not_found(conn):
    ok, msg = change_password(conn, 9999, "anypass", "newpass")
    assert ok is False


# ── delete_account ────────────────────────────────────────────────────────────

def test_delete_account_soft_deletes_user(conn):
    register_user(conn, "a@example.com", "user1", "pass")
    delete_account(conn, _uid(conn, "user1"))
    row = conn.execute("SELECT deleted_at FROM users WHERE username='user1'").fetchone()
    assert row["deleted_at"] is not None


def test_delete_account_blocks_authenticate(conn):
    register_user(conn, "a@example.com", "user1", "pass")
    delete_account(conn, _uid(conn, "user1"))
    assert authenticate(conn, "a@example.com", "pass") is None


def test_delete_account_removes_owned_rooms(conn):
    from services.room import create_room
    register_user(conn, "a@example.com", "user1", "pass")
    uid = _uid(conn, "user1")
    create_room(conn, "myroom", "", "public", uid)
    delete_account(conn, uid)
    assert conn.execute("SELECT id FROM rooms WHERE owner_id=?", (uid,)).fetchall() == []


def test_delete_account_removes_memberships(conn):
    from services.room import create_room, join_room
    register_user(conn, "a@example.com", "user1", "pass")
    register_user(conn, "b@example.com", "user2", "pass")
    uid1, uid2 = _uid(conn, "user1"), _uid(conn, "user2")
    rid = create_room(conn, "shared", "", "public", uid1)
    join_room(conn, rid, uid2)
    delete_account(conn, uid2)
    row = conn.execute("SELECT 1 FROM room_members WHERE user_id=?", (uid2,)).fetchone()
    assert row is None
