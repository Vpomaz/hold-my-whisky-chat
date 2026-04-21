import sqlite3
import pytest
from services.message import get_messages, send_message, edit_message, delete_message


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    with open("sql/init_schema.sql") as f:
        c.executescript(f.read())
    c.execute("INSERT INTO users (id, email, username, password_hash) VALUES (1,'a@x.com','alice','x')")
    c.execute("INSERT INTO rooms (id, name, description, visibility, owner_id) VALUES (1,'general','',  'public',1)")
    c.execute("INSERT INTO room_members (room_id, user_id, role) VALUES (1,1,'owner')")
    c.commit()
    yield c
    c.close()


def test_send_message_returns_id(conn):
    mid = send_message(conn, room_id=1, author_id=1, content="hello")
    assert mid == 1


def test_get_messages_returns_sent(conn):
    send_message(conn, 1, 1, "hello")
    msgs = get_messages(conn, room_id=1)
    assert len(msgs) == 1
    assert msgs[0]["content"] == "hello"
    assert msgs[0]["author"] == "alice"


def test_get_messages_chronological_order(conn):
    send_message(conn, 1, 1, "first")
    send_message(conn, 1, 1, "second")
    msgs = get_messages(conn, room_id=1)
    assert msgs[0]["content"] == "first"
    assert msgs[1]["content"] == "second"


def test_get_messages_before_id_paginates(conn):
    id1 = send_message(conn, 1, 1, "first")
    send_message(conn, 1, 1, "second")
    msgs = get_messages(conn, room_id=1, before_id=id1 + 1)
    assert len(msgs) == 1
    assert msgs[0]["content"] == "first"


def test_get_messages_excludes_deleted(conn):
    mid = send_message(conn, 1, 1, "bye")
    delete_message(conn, mid)
    msgs = get_messages(conn, room_id=1)
    assert msgs == []


def test_get_messages_empty_room(conn):
    assert get_messages(conn, room_id=1) == []


def test_edit_message_updates_content(conn):
    mid = send_message(conn, 1, 1, "original")
    edit_message(conn, mid, author_id=1, content="updated")
    msgs = get_messages(conn, room_id=1)
    assert msgs[0]["content"] == "updated"
    assert msgs[0]["edited_at"] is not None


def test_edit_message_wrong_author_no_change(conn):
    mid = send_message(conn, 1, 1, "original")
    edit_message(conn, mid, author_id=99, content="hacked")
    msgs = get_messages(conn, room_id=1)
    assert msgs[0]["content"] == "original"


def test_send_message_with_reply(conn):
    id1 = send_message(conn, 1, 1, "parent")
    id2 = send_message(conn, 1, 1, "reply", reply_to_id=id1)
    msgs = get_messages(conn, room_id=1)
    assert msgs[1]["reply_to_id"] == id1


def test_delete_message_soft_deletes(conn):
    mid = send_message(conn, 1, 1, "temp")
    delete_message(conn, mid)
    row = conn.execute("SELECT deleted_at FROM messages WHERE id=?", (mid,)).fetchone()
    assert row["deleted_at"] is not None
