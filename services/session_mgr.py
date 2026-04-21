import sqlite3
import uuid


def create_session(
    conn: sqlite3.Connection,
    user_id: int,
    user_agent: str = "",
    ip_address: str = "",
) -> str:
    session_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO user_sessions (id, user_id, user_agent, ip_address, presence) "
        "VALUES (?,?,?,?,'online')",
        (session_id, user_id, user_agent, ip_address),
    )
    conn.commit()
    return session_id


def get_sessions(conn: sqlite3.Connection, user_id: int) -> list:
    return conn.execute(
        """
        SELECT id, user_agent, ip_address, created_at, last_seen, presence
        FROM user_sessions WHERE user_id=?
        ORDER BY last_seen DESC
        """,
        (user_id,),
    ).fetchall()


def delete_session(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute("DELETE FROM user_sessions WHERE id=?", (session_id,))
    conn.commit()


def update_presence(conn: sqlite3.Connection, session_id: str, presence: str) -> None:
    conn.execute(
        "UPDATE user_sessions SET presence=?, last_seen=datetime('now') WHERE id=?",
        (presence, session_id),
    )
    conn.commit()
