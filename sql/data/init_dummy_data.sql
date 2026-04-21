-- Passwords are bcrypt of "password123"
-- alice = admin, bob + carol = user
INSERT OR IGNORE INTO users (id, email, username, password_hash, role) VALUES
(1, 'alice@example.com', 'alice', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'admin'),
(2, 'bob@example.com',   'bob',   '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'user'),
(3, 'carol@example.com', 'carol', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'user');

INSERT OR IGNORE INTO rooms (id, name, description, visibility, owner_id) VALUES
(1, 'general',     'General discussion',  'public',  1),
(2, 'engineering', 'Tech talk',           'public',  1),
(3, 'core-team',   'Private team room',   'private', 1);

INSERT OR IGNORE INTO room_members (room_id, user_id, role) VALUES
(1, 1, 'owner'), (1, 2, 'member'), (1, 3, 'member'),
(2, 1, 'owner'), (2, 2, 'admin'),
(3, 1, 'owner'), (3, 2, 'member');

INSERT OR IGNORE INTO friendships (requester_id, addressee_id, status) VALUES
(1, 2, 'accepted'),
(1, 3, 'accepted');

INSERT OR IGNORE INTO messages (room_id, author_id, content) VALUES
(1, 2, 'Hello team!'),
(1, 1, 'Welcome everyone'),
(2, 2, 'Anyone up for a code review?');
