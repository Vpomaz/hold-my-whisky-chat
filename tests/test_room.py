import sqlite3
import pytest
from services.room import get_public_rooms, get_user_rooms, create_room


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
