import sqlite3
import pytest
from services.auth import register_user, authenticate, hash_password, verify_password


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    with open("sql/init_schema.sql") as f:
        c.executescript(f.read())
    yield c
    c.close()


def test_hash_and_verify():
    h = hash_password("secret")
    assert verify_password("secret", h)
    assert not verify_password("wrong", h)


def test_register_and_authenticate(conn):
    register_user(conn, "u@example.com", "user1", "pass123")
    result = authenticate(conn, "u@example.com", "pass123")
    assert result is not None
    assert result["username"] == "user1"


def test_wrong_password(conn):
    register_user(conn, "u@example.com", "user1", "pass123")
    assert authenticate(conn, "u@example.com", "wrong") is None
