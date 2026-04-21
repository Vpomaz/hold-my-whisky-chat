import sqlite3


def get_all_rooms(conn: sqlite3.Connection) -> list:
    return conn.execute(
        "SELECT id, name, description, visibility, owner_id FROM rooms ORDER BY name"
    ).fetchall()


def get_room(conn: sqlite3.Connection, room_id: int):
    return conn.execute(
        "SELECT id, name, description, visibility, owner_id FROM rooms WHERE id=?",
        (room_id,),
    ).fetchone()


def get_room_members(conn: sqlite3.Connection, room_id: int) -> list:
    return conn.execute(
        """
        SELECT u.id, u.username, rm.role,
               COALESCE(
                   CASE MAX(
                       CASE s.presence WHEN 'online' THEN 3 WHEN 'afk' THEN 2 ELSE 1 END
                   )
                   WHEN 3 THEN 'online' WHEN 2 THEN 'afk' ELSE 'offline' END,
                   'offline'
               ) AS presence
        FROM room_members rm
        JOIN users u ON u.id = rm.user_id
        LEFT JOIN user_sessions s ON s.user_id = u.id
        WHERE rm.room_id = ?
        GROUP BY u.id, u.username, rm.role
        ORDER BY
            CASE rm.role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END,
            u.username
        """,
        (room_id,),
    ).fetchall()


def get_room_bans(conn: sqlite3.Connection, room_id: int) -> list:
    return conn.execute(
        """
        SELECT rb.user_id, u.username AS banned_username,
               b.username AS banned_by_username, rb.banned_at
        FROM room_bans rb
        JOIN users u ON u.id = rb.user_id
        JOIN users b ON b.id = rb.banned_by
        WHERE rb.room_id = ?
        ORDER BY rb.banned_at DESC
        """,
        (room_id,),
    ).fetchall()


def get_room_invitations(conn: sqlite3.Connection, room_id: int) -> list:
    return conn.execute(
        """
        SELECT u.username AS invitee_username, inv.username AS inviter_username,
               ri.created_at
        FROM room_invitations ri
        JOIN users u ON u.id = ri.invitee_id
        JOIN users inv ON inv.id = ri.inviter_id
        WHERE ri.room_id = ?
        ORDER BY ri.created_at DESC
        """,
        (room_id,),
    ).fetchall()


def make_admin(conn: sqlite3.Connection, room_id: int, user_id: int) -> None:
    conn.execute(
        "UPDATE room_members SET role='admin' WHERE room_id=? AND user_id=?",
        (room_id, user_id),
    )
    conn.commit()


def remove_admin(conn: sqlite3.Connection, room_id: int, user_id: int) -> None:
    conn.execute(
        "UPDATE room_members SET role='member' WHERE room_id=? AND user_id=?",
        (room_id, user_id),
    )
    conn.commit()


def ban_member(conn: sqlite3.Connection, room_id: int, user_id: int, banned_by_id: int) -> None:
    conn.execute("DELETE FROM room_members WHERE room_id=? AND user_id=?", (room_id, user_id))
    conn.execute(
        "INSERT OR IGNORE INTO room_bans (room_id, user_id, banned_by) VALUES (?, ?, ?)",
        (room_id, user_id, banned_by_id),
    )
    conn.commit()


def unban_member(conn: sqlite3.Connection, room_id: int, user_id: int) -> None:
    conn.execute("DELETE FROM room_bans WHERE room_id=? AND user_id=?", (room_id, user_id))
    conn.commit()


def send_invitation(
    conn: sqlite3.Connection, room_id: int, inviter_id: int, invitee_username: str
) -> tuple[bool, str]:
    user = conn.execute(
        "SELECT id FROM users WHERE username=? AND deleted_at IS NULL", (invitee_username,)
    ).fetchone()
    if not user:
        return False, "User not found"
    already = conn.execute(
        "SELECT 1 FROM room_members WHERE room_id=? AND user_id=?", (room_id, user["id"])
    ).fetchone()
    if already:
        return False, "User is already a member"
    try:
        conn.execute(
            "INSERT INTO room_invitations (room_id, inviter_id, invitee_id) VALUES (?, ?, ?)",
            (room_id, inviter_id, user["id"]),
        )
        conn.commit()
        return True, "Invitation sent"
    except Exception as exc:
        return False, str(exc)


def update_room(
    conn: sqlite3.Connection, room_id: int, name: str, description: str, visibility: str
) -> tuple[bool, str]:
    try:
        conn.execute(
            "UPDATE rooms SET name=?, description=?, visibility=? WHERE id=?",
            (name, description, visibility, room_id),
        )
        conn.commit()
        return True, "Changes saved"
    except Exception as exc:
        return False, str(exc)


def delete_room_by_id(conn: sqlite3.Connection, room_id: int) -> None:
    conn.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    conn.commit()


def get_public_rooms(conn: sqlite3.Connection, search: str = "") -> list:
    query = """
        SELECT r.id, r.name, r.description, COUNT(rm.user_id) AS member_count
        FROM rooms r
        LEFT JOIN room_members rm ON rm.room_id = r.id
        WHERE r.visibility = 'public' AND r.name LIKE ?
        GROUP BY r.id
        ORDER BY r.name
    """
    return conn.execute(query, (f"%{search}%",)).fetchall()


def get_user_rooms(conn: sqlite3.Connection, user_id: int) -> list:
    return conn.execute(
        """
        SELECT r.id, r.name, r.visibility, rm.role
        FROM rooms r
        JOIN room_members rm ON rm.room_id = r.id
        WHERE rm.user_id = ?
        ORDER BY r.name
        """,
        (user_id,),
    ).fetchall()


def create_room(conn: sqlite3.Connection, name: str, description: str, visibility: str, owner_id: int) -> int:
    cur = conn.execute(
        "INSERT INTO rooms (name, description, visibility, owner_id) VALUES (?, ?, ?, ?)",
        (name, description, visibility, owner_id),
    )
    room_id = cur.lastrowid
    conn.execute(
        "INSERT INTO room_members (room_id, user_id, role) VALUES (?, ?, 'owner')",
        (room_id, owner_id),
    )
    conn.commit()
    return room_id
