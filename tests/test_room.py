import sqlite3
import pytest
from services.room import (
    get_all_rooms, get_room, get_room_members, get_room_bans, get_room_invitations,
    make_admin, remove_admin, ban_member, unban_member,
    send_invitation, update_room, delete_room_by_id,
    get_public_rooms, get_user_rooms, create_room,
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
    c.commit()
    yield c
    c.close()


def test_create_room_returns_id(conn):
    room_id = create_room(conn, "general", "desc", "public", 1)
    assert room_id == 1


def test_create_room_adds_owner_as_member(conn):
    room_id = create_room(conn, "general", "desc", "public", 1)
    row = conn.execute("SELECT role FROM room_members WHERE room_id=? AND user_id=1", (room_id,)).fetchone()
    assert row["role"] == "owner"


def test_get_public_rooms_returns_only_public(conn):
    create_room(conn, "public-room", "desc", "public", 1)
    create_room(conn, "private-room", "desc", "private", 1)
    rooms = get_public_rooms(conn)
    names = [r["name"] for r in rooms]
    assert "public-room" in names
    assert "private-room" not in names


def test_get_public_rooms_search_filters(conn):
    create_room(conn, "python-talk", "desc", "public", 1)
    create_room(conn, "random", "desc", "public", 1)
    results = get_public_rooms(conn, search="python")
    assert len(results) == 1
    assert results[0]["name"] == "python-talk"


def test_get_public_rooms_empty_search_returns_all_public(conn):
    create_room(conn, "room-a", "desc", "public", 1)
    create_room(conn, "room-b", "desc", "public", 1)
    results = get_public_rooms(conn)
    assert len(results) == 2


def test_get_public_rooms_member_count(conn):
    room_id = create_room(conn, "general", "desc", "public", 1)
    conn.execute("INSERT INTO room_members (room_id, user_id, role) VALUES (?,2,'member')", (room_id,))
    conn.commit()
    rooms = get_public_rooms(conn)
    assert rooms[0]["member_count"] == 2


def test_get_user_rooms_returns_joined_rooms(conn):
    create_room(conn, "general", "desc", "public", 1)
    create_room(conn, "other", "desc", "public", 2)
    rooms = get_user_rooms(conn, 1)
    names = [r["name"] for r in rooms]
    assert "general" in names
    assert "other" not in names


def test_get_user_rooms_empty_for_nonmember(conn):
    create_room(conn, "general", "desc", "public", 1)
    rooms = get_user_rooms(conn, 2)
    assert rooms == []


def test_create_room_duplicate_name_raises(conn):
    create_room(conn, "general", "desc", "public", 1)
    with pytest.raises(Exception):
        create_room(conn, "general", "other desc", "public", 2)


# ── get_all_rooms ─────────────────────────────────────────────────────────────

def test_get_all_rooms_returns_all(conn):
    create_room(conn, "alpha", "d", "public", 1)
    create_room(conn, "beta", "d", "private", 2)
    rooms = get_all_rooms(conn)
    names = [r["name"] for r in rooms]
    assert "alpha" in names and "beta" in names


def test_get_all_rooms_empty(conn):
    assert get_all_rooms(conn) == []


def test_get_all_rooms_ordered_by_name(conn):
    create_room(conn, "zebra", "d", "public", 1)
    create_room(conn, "alpha", "d", "public", 1)
    names = [r["name"] for r in get_all_rooms(conn)]
    assert names == sorted(names)


# ── get_room ──────────────────────────────────────────────────────────────────

def test_get_room_returns_correct_room(conn):
    room_id = create_room(conn, "general", "desc", "public", 1)
    room = get_room(conn, room_id)
    assert room["name"] == "general"
    assert room["visibility"] == "public"


def test_get_room_returns_none_for_missing(conn):
    assert get_room(conn, 999) is None


# ── get_room_members ──────────────────────────────────────────────────────────

def test_get_room_members_includes_owner(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    members = get_room_members(conn, room_id)
    roles = [m["role"] for m in members]
    assert "owner" in roles


def test_get_room_members_ordered_owner_first(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    conn.execute("INSERT INTO room_members (room_id, user_id, role) VALUES (?,2,'member')", (room_id,))
    conn.commit()
    members = get_room_members(conn, room_id)
    assert members[0]["role"] == "owner"


def test_get_room_members_presence_defaults_offline(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    members = get_room_members(conn, room_id)
    assert members[0]["presence"] == "offline"


def test_get_room_members_empty_room(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    conn.execute("DELETE FROM room_members WHERE room_id=?", (room_id,))
    conn.commit()
    assert get_room_members(conn, room_id) == []


# ── get_room_bans ─────────────────────────────────────────────────────────────

def test_get_room_bans_returns_banned_user(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    ban_member(conn, room_id, 2, 1)
    bans = get_room_bans(conn, room_id)
    assert len(bans) == 1
    assert bans[0]["banned_username"] == "bob"
    assert bans[0]["banned_by_username"] == "alice"


def test_get_room_bans_empty(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    assert get_room_bans(conn, room_id) == []


# ── get_room_invitations ──────────────────────────────────────────────────────

def test_get_room_invitations_returns_pending(conn):
    room_id = create_room(conn, "general", "d", "private", 1)
    ok, _ = send_invitation(conn, room_id, 1, "bob")
    assert ok
    invitations = get_room_invitations(conn, room_id)
    assert len(invitations) == 1
    assert invitations[0]["invitee_username"] == "bob"


def test_get_room_invitations_empty(conn):
    room_id = create_room(conn, "general", "d", "private", 1)
    assert get_room_invitations(conn, room_id) == []


# ── make_admin / remove_admin ─────────────────────────────────────────────────

def test_make_admin_promotes_member(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    conn.execute("INSERT INTO room_members (room_id, user_id, role) VALUES (?,2,'member')", (room_id,))
    conn.commit()
    make_admin(conn, room_id, 2)
    row = conn.execute("SELECT role FROM room_members WHERE room_id=? AND user_id=2", (room_id,)).fetchone()
    assert row["role"] == "admin"


def test_remove_admin_demotes_to_member(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    conn.execute("INSERT INTO room_members (room_id, user_id, role) VALUES (?,2,'admin')", (room_id,))
    conn.commit()
    remove_admin(conn, room_id, 2)
    row = conn.execute("SELECT role FROM room_members WHERE room_id=? AND user_id=2", (room_id,)).fetchone()
    assert row["role"] == "member"


# ── ban_member / unban_member ─────────────────────────────────────────────────

def test_ban_member_removes_from_room(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    conn.execute("INSERT INTO room_members (room_id, user_id, role) VALUES (?,2,'member')", (room_id,))
    conn.commit()
    ban_member(conn, room_id, 2, 1)
    row = conn.execute("SELECT 1 FROM room_members WHERE room_id=? AND user_id=2", (room_id,)).fetchone()
    assert row is None


def test_ban_member_adds_to_room_bans(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    conn.execute("INSERT INTO room_members (room_id, user_id, role) VALUES (?,2,'member')", (room_id,))
    conn.commit()
    ban_member(conn, room_id, 2, 1)
    row = conn.execute("SELECT 1 FROM room_bans WHERE room_id=? AND user_id=2", (room_id,)).fetchone()
    assert row is not None


def test_ban_member_idempotent(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    ban_member(conn, room_id, 2, 1)
    ban_member(conn, room_id, 2, 1)  # second call should not raise
    bans = get_room_bans(conn, room_id)
    assert len(bans) == 1


def test_unban_member_removes_ban(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    ban_member(conn, room_id, 2, 1)
    unban_member(conn, room_id, 2)
    row = conn.execute("SELECT 1 FROM room_bans WHERE room_id=? AND user_id=2", (room_id,)).fetchone()
    assert row is None


# ── send_invitation ───────────────────────────────────────────────────────────

def test_send_invitation_success(conn):
    room_id = create_room(conn, "private-room", "d", "private", 1)
    ok, msg = send_invitation(conn, room_id, 1, "bob")
    assert ok is True
    assert "sent" in msg.lower()


def test_send_invitation_user_not_found(conn):
    room_id = create_room(conn, "private-room", "d", "private", 1)
    ok, msg = send_invitation(conn, room_id, 1, "nonexistent")
    assert ok is False
    assert "not found" in msg.lower()


def test_send_invitation_already_member(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    ok, msg = send_invitation(conn, room_id, 2, "alice")  # alice is owner/member
    assert ok is False
    assert "already" in msg.lower()


def test_send_invitation_duplicate_raises(conn):
    room_id = create_room(conn, "private-room", "d", "private", 1)
    send_invitation(conn, room_id, 1, "bob")
    ok, _ = send_invitation(conn, room_id, 1, "bob")  # duplicate
    assert ok is False


# ── update_room ───────────────────────────────────────────────────────────────

def test_update_room_changes_fields(conn):
    room_id = create_room(conn, "general", "old desc", "public", 1)
    ok, msg = update_room(conn, room_id, "new-name", "new desc", "private")
    assert ok is True
    room = get_room(conn, room_id)
    assert room["name"] == "new-name"
    assert room["description"] == "new desc"
    assert room["visibility"] == "private"


def test_update_room_duplicate_name_fails(conn):
    create_room(conn, "room-a", "d", "public", 1)
    room_b_id = create_room(conn, "room-b", "d", "public", 2)
    ok, msg = update_room(conn, room_b_id, "room-a", "d", "public")
    assert ok is False


# ── delete_room_by_id ─────────────────────────────────────────────────────────

def test_delete_room_by_id_removes_room(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    delete_room_by_id(conn, room_id)
    assert get_room(conn, room_id) is None


def test_delete_room_by_id_cascades_members(conn):
    room_id = create_room(conn, "general", "d", "public", 1)
    delete_room_by_id(conn, room_id)
    rows = conn.execute("SELECT 1 FROM room_members WHERE room_id=?", (room_id,)).fetchall()
    assert rows == []
