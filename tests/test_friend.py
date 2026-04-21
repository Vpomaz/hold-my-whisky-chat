import sqlite3
import pytest
from services.friend import (
    get_friends, get_pending_incoming, get_pending_outgoing,
    send_friend_request, accept_request, decline_request,
    remove_friend, block_user, unblock_user, get_blocked_users,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    with open("sql/init_schema.sql") as f:
        c.executescript(f.read())
    c.execute("INSERT INTO users (id, email, username, password_hash) VALUES (1,'a@x.com','alice','x')")
    c.execute("INSERT INTO users (id, email, username, password_hash) VALUES (2,'b@x.com','bob','x')")
    c.execute("INSERT INTO users (id, email, username, password_hash) VALUES (3,'c@x.com','carol','x')")
    c.commit()
    yield c
    c.close()


def _make_friends(conn, uid1, uid2):
    conn.execute(
        "INSERT INTO friendships (requester_id, addressee_id, status) VALUES (?,?,'accepted')",
        (uid1, uid2),
    )
    conn.commit()


def _make_pending(conn, requester_id, addressee_id, message=""):
    conn.execute(
        "INSERT INTO friendships (requester_id, addressee_id, status, message) VALUES (?,?,'pending',?)",
        (requester_id, addressee_id, message),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


# ── get_friends ───────────────────────────────────────────────────────────────

def test_get_friends_returns_accepted(conn):
    _make_friends(conn, 1, 2)
    friends = get_friends(conn, 1)
    assert len(friends) == 1
    assert friends[0]["username"] == "bob"


def test_get_friends_empty(conn):
    assert get_friends(conn, 1) == []


def test_get_friends_excludes_pending(conn):
    _make_pending(conn, 1, 2)
    assert get_friends(conn, 1) == []


def test_get_friends_works_from_addressee_side(conn):
    _make_friends(conn, 1, 2)
    friends = get_friends(conn, 2)
    assert len(friends) == 1
    assert friends[0]["username"] == "alice"


# ── get_pending_incoming ──────────────────────────────────────────────────────

def test_get_pending_incoming_returns_requests(conn):
    _make_pending(conn, 1, 2, "hey!")
    reqs = get_pending_incoming(conn, 2)
    assert len(reqs) == 1
    assert reqs[0]["requester_username"] == "alice"
    assert reqs[0]["message"] == "hey!"


def test_get_pending_incoming_empty(conn):
    assert get_pending_incoming(conn, 2) == []


def test_get_pending_incoming_excludes_accepted(conn):
    _make_friends(conn, 1, 2)
    assert get_pending_incoming(conn, 2) == []


# ── get_pending_outgoing ──────────────────────────────────────────────────────

def test_get_pending_outgoing_returns_sent_requests(conn):
    _make_pending(conn, 1, 2)
    reqs = get_pending_outgoing(conn, 1)
    assert len(reqs) == 1
    assert reqs[0]["addressee_username"] == "bob"


def test_get_pending_outgoing_empty(conn):
    assert get_pending_outgoing(conn, 1) == []


# ── send_friend_request ───────────────────────────────────────────────────────

def test_send_friend_request_success(conn):
    ok, msg = send_friend_request(conn, 1, "bob")
    assert ok is True
    assert "sent" in msg.lower()


def test_send_friend_request_with_message(conn):
    ok, _ = send_friend_request(conn, 1, "bob", "Hi there!")
    assert ok is True
    row = conn.execute("SELECT message FROM friendships WHERE requester_id=1 AND addressee_id=2").fetchone()
    assert row["message"] == "Hi there!"


def test_send_friend_request_user_not_found(conn):
    ok, msg = send_friend_request(conn, 1, "nobody")
    assert ok is False
    assert "not found" in msg.lower()


def test_send_friend_request_to_self(conn):
    ok, msg = send_friend_request(conn, 1, "alice")
    assert ok is False
    assert "yourself" in msg.lower()


def test_send_friend_request_already_pending(conn):
    send_friend_request(conn, 1, "bob")
    ok, msg = send_friend_request(conn, 1, "bob")
    assert ok is False
    assert "already" in msg.lower()


def test_send_friend_request_already_friends(conn):
    _make_friends(conn, 1, 2)
    ok, msg = send_friend_request(conn, 1, "bob")
    assert ok is False
    assert "friends" in msg.lower()


def test_send_friend_request_blocked_by_target(conn):
    conn.execute("INSERT INTO user_bans (banner_id, banned_id) VALUES (2,1)")
    conn.commit()
    ok, msg = send_friend_request(conn, 1, "bob")
    assert ok is False


def test_send_friend_request_blocked_target(conn):
    conn.execute("INSERT INTO user_bans (banner_id, banned_id) VALUES (1,2)")
    conn.commit()
    ok, msg = send_friend_request(conn, 1, "bob")
    assert ok is False


# ── accept_request ────────────────────────────────────────────────────────────

def test_accept_request_success(conn):
    fid = _make_pending(conn, 1, 2)
    ok, msg = accept_request(conn, fid, 2)
    assert ok is True
    row = conn.execute("SELECT status FROM friendships WHERE id=?", (fid,)).fetchone()
    assert row["status"] == "accepted"


def test_accept_request_not_found(conn):
    ok, msg = accept_request(conn, 9999, 2)
    assert ok is False
    assert "not found" in msg.lower()


def test_accept_request_wrong_user(conn):
    fid = _make_pending(conn, 1, 2)
    ok, msg = accept_request(conn, fid, 3)
    assert ok is False


# ── decline_request ───────────────────────────────────────────────────────────

def test_decline_request_deletes_row(conn):
    fid = _make_pending(conn, 1, 2)
    decline_request(conn, fid)
    assert conn.execute("SELECT id FROM friendships WHERE id=?", (fid,)).fetchone() is None


# ── remove_friend ─────────────────────────────────────────────────────────────

def test_remove_friend_from_requester_side(conn):
    _make_friends(conn, 1, 2)
    remove_friend(conn, 1, 2)
    assert get_friends(conn, 1) == []


def test_remove_friend_from_addressee_side(conn):
    _make_friends(conn, 1, 2)
    remove_friend(conn, 2, 1)
    assert get_friends(conn, 2) == []


# ── block_user ────────────────────────────────────────────────────────────────

def test_block_user_success(conn):
    ok, msg = block_user(conn, 1, "bob")
    assert ok is True
    row = conn.execute("SELECT 1 FROM user_bans WHERE banner_id=1 AND banned_id=2").fetchone()
    assert row is not None


def test_block_user_removes_friendship(conn):
    _make_friends(conn, 1, 2)
    block_user(conn, 1, "bob")
    assert get_friends(conn, 1) == []


def test_block_user_not_found(conn):
    ok, msg = block_user(conn, 1, "nobody")
    assert ok is False
    assert "not found" in msg.lower()


def test_block_user_self(conn):
    ok, msg = block_user(conn, 1, "alice")
    assert ok is False
    assert "yourself" in msg.lower()


def test_block_user_idempotent(conn):
    block_user(conn, 1, "bob")
    ok, _ = block_user(conn, 1, "bob")
    assert ok is True  # OR IGNORE means no error


# ── unblock_user ──────────────────────────────────────────────────────────────

def test_unblock_user_removes_ban(conn):
    block_user(conn, 1, "bob")
    unblock_user(conn, 1, 2)
    row = conn.execute("SELECT 1 FROM user_bans WHERE banner_id=1 AND banned_id=2").fetchone()
    assert row is None


def test_unblock_nonexistent_is_noop(conn):
    unblock_user(conn, 1, 2)  # should not raise


# ── get_blocked_users ─────────────────────────────────────────────────────────

def test_get_blocked_users_returns_blocked(conn):
    block_user(conn, 1, "bob")
    blocked = get_blocked_users(conn, 1)
    assert len(blocked) == 1
    assert blocked[0]["username"] == "bob"


def test_get_blocked_users_empty(conn):
    assert get_blocked_users(conn, 1) == []


def test_get_blocked_users_only_own(conn):
    block_user(conn, 2, "carol")
    assert get_blocked_users(conn, 1) == []
