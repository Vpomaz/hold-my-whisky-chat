import sqlite3


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
