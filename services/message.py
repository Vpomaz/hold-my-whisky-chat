import sqlite3

PAGE_SIZE = 50


def get_messages(conn: sqlite3.Connection, room_id: int, before_id: int | None = None) -> list:
    """Return up to PAGE_SIZE messages older than before_id (for infinite scroll)."""
    if before_id:
        rows = conn.execute(
            """
            SELECT m.id, m.content, m.created_at, m.edited_at, m.reply_to_id,
                   u.username AS author
            FROM messages m JOIN users u ON u.id = m.author_id
            WHERE m.room_id = ? AND m.deleted_at IS NULL AND m.id < ?
            ORDER BY m.id DESC LIMIT ?
            """,
            (room_id, before_id, PAGE_SIZE),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT m.id, m.content, m.created_at, m.edited_at, m.reply_to_id,
                   u.username AS author
            FROM messages m JOIN users u ON u.id = m.author_id
            WHERE m.room_id = ? AND m.deleted_at IS NULL
            ORDER BY m.id DESC LIMIT ?
            """,
            (room_id, PAGE_SIZE),
        ).fetchall()
    return list(reversed(rows))


def send_message(conn: sqlite3.Connection, room_id: int, author_id: int, content: str, reply_to_id: int | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO messages (room_id, author_id, content, reply_to_id) VALUES (?, ?, ?, ?)",
        (room_id, author_id, content, reply_to_id),
    )
    conn.commit()
    return cur.lastrowid


def edit_message(conn: sqlite3.Connection, message_id: int, author_id: int, content: str) -> None:
    conn.execute(
        "UPDATE messages SET content = ?, edited_at = datetime('now') WHERE id = ? AND author_id = ?",
        (content, message_id, author_id),
    )
    conn.commit()


def delete_message(conn: sqlite3.Connection, message_id: int) -> None:
    conn.execute(
        "UPDATE messages SET deleted_at = datetime('now') WHERE id = ?",
        (message_id,),
    )
    conn.commit()
