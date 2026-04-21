import bcrypt
import sqlite3


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def register_user(conn: sqlite3.Connection, email: str, username: str, password: str) -> int:
    cur = conn.execute(
        "INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
        (email, username, hash_password(password)),
    )
    conn.commit()
    return cur.lastrowid


def update_email(conn: sqlite3.Connection, user_id: int, new_email: str) -> tuple[bool, str]:
    try:
        conn.execute("UPDATE users SET email=? WHERE id=?", (new_email, user_id))
        conn.commit()
        return True, "Email updated"
    except Exception as exc:
        return False, "Email already taken" if "UNIQUE" in str(exc) else str(exc)


def change_password(
    conn: sqlite3.Connection, user_id: int, old_password: str, new_password: str
) -> tuple[bool, str]:
    row = conn.execute(
        "SELECT password_hash FROM users WHERE id=?", (user_id,)
    ).fetchone()
    if not row or not verify_password(old_password, row["password_hash"]):
        return False, "Current password is incorrect"
    conn.execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (hash_password(new_password), user_id),
    )
    conn.commit()
    return True, "Password changed"


def delete_account(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("DELETE FROM rooms WHERE owner_id=?", (user_id,))
    conn.execute("DELETE FROM room_members WHERE user_id=?", (user_id,))
    conn.execute("UPDATE users SET deleted_at=datetime('now') WHERE id=?", (user_id,))
    conn.commit()


def authenticate(conn: sqlite3.Connection, email: str, password: str) -> dict | None:
    row = conn.execute(
        "SELECT id, username, password_hash, role FROM users WHERE email = ? AND deleted_at IS NULL",
        (email,),
    ).fetchone()
    if row and verify_password(password, row["password_hash"]):
        return {"id": row["id"], "username": row["username"], "role": row["role"]}
    return None
