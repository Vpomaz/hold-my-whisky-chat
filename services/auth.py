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


def authenticate(conn: sqlite3.Connection, email: str, password: str) -> dict | None:
    row = conn.execute(
        "SELECT id, username, password_hash FROM users WHERE email = ? AND deleted_at IS NULL",
        (email,),
    ).fetchone()
    if row and verify_password(password, row["password_hash"]):
        return {"id": row["id"], "username": row["username"]}
    return None
