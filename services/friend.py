import sqlite3

_PRESENCE_RANK = "CASE s.presence WHEN 'online' THEN 3 WHEN 'afk' THEN 2 ELSE 1 END"
_PRESENCE_LABEL = f"COALESCE(CASE MAX({_PRESENCE_RANK}) WHEN 3 THEN 'online' WHEN 2 THEN 'afk' ELSE 'offline' END, 'offline')"


def get_friends(conn: sqlite3.Connection, user_id: int) -> list:
    return conn.execute(
        f"""
        SELECT f.id, u.id AS friend_id, u.username, {_PRESENCE_LABEL} AS presence
        FROM friendships f
        JOIN users u ON u.id = CASE WHEN f.requester_id=? THEN f.addressee_id ELSE f.requester_id END
        LEFT JOIN user_sessions s ON s.user_id = u.id
        WHERE (f.requester_id=? OR f.addressee_id=?) AND f.status='accepted' AND u.deleted_at IS NULL
        GROUP BY f.id, u.id, u.username
        ORDER BY u.username
        """,
        (user_id, user_id, user_id),
    ).fetchall()


def get_pending_incoming(conn: sqlite3.Connection, user_id: int) -> list:
    return conn.execute(
        """
        SELECT f.id, u.username AS requester_username, f.message, f.created_at
        FROM friendships f
        JOIN users u ON u.id = f.requester_id
        WHERE f.addressee_id=? AND f.status='pending' AND u.deleted_at IS NULL
        ORDER BY f.created_at DESC
        """,
        (user_id,),
    ).fetchall()


def get_pending_outgoing(conn: sqlite3.Connection, user_id: int) -> list:
    return conn.execute(
        """
        SELECT f.id, u.username AS addressee_username, f.message, f.created_at
        FROM friendships f
        JOIN users u ON u.id = f.addressee_id
        WHERE f.requester_id=? AND f.status='pending' AND u.deleted_at IS NULL
        ORDER BY f.created_at DESC
        """,
        (user_id,),
    ).fetchall()


def send_friend_request(
    conn: sqlite3.Connection, requester_id: int, addressee_username: str, message: str = ""
) -> tuple[bool, str]:
    user = conn.execute(
        "SELECT id FROM users WHERE username=? AND deleted_at IS NULL", (addressee_username,)
    ).fetchone()
    if not user:
        return False, "User not found"
    if user["id"] == requester_id:
        return False, "Cannot send a request to yourself"
    existing = conn.execute(
        """SELECT status FROM friendships
           WHERE (requester_id=? AND addressee_id=?) OR (requester_id=? AND addressee_id=?)""",
        (requester_id, user["id"], user["id"], requester_id),
    ).fetchone()
    if existing:
        return (False, "Already friends") if existing["status"] == "accepted" else (False, "Request already sent")
    banned = conn.execute(
        """SELECT 1 FROM user_bans
           WHERE (banner_id=? AND banned_id=?) OR (banner_id=? AND banned_id=?)""",
        (requester_id, user["id"], user["id"], requester_id),
    ).fetchone()
    if banned:
        return False, "Cannot send request to this user"
    try:
        conn.execute(
            "INSERT INTO friendships (requester_id, addressee_id, message) VALUES (?,?,?)",
            (requester_id, user["id"], message),
        )
        conn.commit()
        return True, "Friend request sent"
    except Exception as exc:
        return False, str(exc)


def accept_request(conn: sqlite3.Connection, friendship_id: int, user_id: int) -> tuple[bool, str]:
    row = conn.execute(
        "SELECT id FROM friendships WHERE id=? AND addressee_id=? AND status='pending'",
        (friendship_id, user_id),
    ).fetchone()
    if not row:
        return False, "Request not found"
    conn.execute("UPDATE friendships SET status='accepted' WHERE id=?", (friendship_id,))
    conn.commit()
    return True, "Friend request accepted"


def decline_request(conn: sqlite3.Connection, friendship_id: int) -> None:
    conn.execute("DELETE FROM friendships WHERE id=?", (friendship_id,))
    conn.commit()


def remove_friend(conn: sqlite3.Connection, user_id: int, friend_id: int) -> None:
    conn.execute(
        """DELETE FROM friendships
           WHERE (requester_id=? AND addressee_id=?) OR (requester_id=? AND addressee_id=?)""",
        (user_id, friend_id, friend_id, user_id),
    )
    conn.commit()


def block_user(
    conn: sqlite3.Connection, banner_id: int, banned_username: str
) -> tuple[bool, str]:
    user = conn.execute(
        "SELECT id FROM users WHERE username=? AND deleted_at IS NULL", (banned_username,)
    ).fetchone()
    if not user:
        return False, "User not found"
    if user["id"] == banner_id:
        return False, "Cannot block yourself"
    try:
        conn.execute(
            "INSERT OR IGNORE INTO user_bans (banner_id, banned_id) VALUES (?,?)",
            (banner_id, user["id"]),
        )
        conn.execute(
            """DELETE FROM friendships
               WHERE (requester_id=? AND addressee_id=?) OR (requester_id=? AND addressee_id=?)""",
            (banner_id, user["id"], user["id"], banner_id),
        )
        conn.commit()
        return True, f"{banned_username} blocked"
    except Exception as exc:
        return False, str(exc)


def unblock_user(conn: sqlite3.Connection, banner_id: int, banned_id: int) -> None:
    conn.execute("DELETE FROM user_bans WHERE banner_id=? AND banned_id=?", (banner_id, banned_id))
    conn.commit()


def get_blocked_users(conn: sqlite3.Connection, user_id: int) -> list:
    return conn.execute(
        """
        SELECT ub.banned_id, u.username, ub.created_at
        FROM user_bans ub
        JOIN users u ON u.id = ub.banned_id
        WHERE ub.banner_id=? AND u.deleted_at IS NULL
        ORDER BY u.username
        """,
        (user_id,),
    ).fetchall()
