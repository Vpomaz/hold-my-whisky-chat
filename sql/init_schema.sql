PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL UNIQUE,
    username    TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at  TEXT
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id          TEXT PRIMARY KEY,  -- UUID
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_agent  TEXT,
    ip_address  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen   TEXT NOT NULL DEFAULT (datetime('now')),
    presence    TEXT NOT NULL DEFAULT 'offline' CHECK (presence IN ('online', 'afk', 'offline'))
);

CREATE TABLE IF NOT EXISTS friendships (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    addressee_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted')),
    message     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (requester_id, addressee_id)
);

CREATE TABLE IF NOT EXISTS user_bans (
    banner_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    banned_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (banner_id, banned_id)
);

CREATE TABLE IF NOT EXISTS rooms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    visibility  TEXT NOT NULL DEFAULT 'public' CHECK (visibility IN ('public', 'private')),
    owner_id    INTEGER NOT NULL REFERENCES users(id),
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS room_members (
    room_id     INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member', 'admin', 'owner')),
    joined_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (room_id, user_id)
);

CREATE TABLE IF NOT EXISTS room_bans (
    room_id     INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    banned_by   INTEGER NOT NULL REFERENCES users(id),
    banned_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (room_id, user_id)
);

CREATE TABLE IF NOT EXISTS room_invitations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id     INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    inviter_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    invitee_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (room_id, invitee_id)
);

-- personal dialogs are represented as a special room-like entity
CREATE TABLE IF NOT EXISTS personal_chats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_a_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_b_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_a_id, user_b_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id     INTEGER REFERENCES rooms(id) ON DELETE CASCADE,
    chat_id     INTEGER REFERENCES personal_chats(id) ON DELETE CASCADE,
    author_id   INTEGER NOT NULL REFERENCES users(id),
    content     TEXT NOT NULL CHECK (length(content) <= 3072),
    reply_to_id INTEGER REFERENCES messages(id),
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    edited_at   TEXT,
    deleted_at  TEXT,
    CHECK ((room_id IS NULL) != (chat_id IS NULL))  -- exactly one of room or chat
);

CREATE TABLE IF NOT EXISTS attachments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id  INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    mime_type   TEXT,
    file_size   INTEGER NOT NULL,
    comment     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_room    ON messages(room_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_chat    ON messages(chat_id, created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_user    ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_members_user     ON room_members(user_id);
