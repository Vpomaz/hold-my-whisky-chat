# hold-my-wisky-chat
Sch-vibe coding chat

# Description
DataArt Agentic Development Hackathon App by Vitalii Pomaz

# Promt history
[here](promt_history.txt)

# Spent time
5 hours 14 minutes

# Spent cost
24.53 USD

# Build & Run
```bash
docker compose up --build
```

# Open app
[localhost:8501](http://localhost:8501)

# Test creds
- admin - alice@example.com / password123
- user - bob@example.com / password123
- user - carol@example.com / password123

# Tasks to be finished

Gap analysis versus `2026_04_18_AI_herders_jam_-_requirements_v3 1.txt` (sections 1–5). Listed items are **not** fully implemented in the current codebase.

| index | section number | feature | notes |
|------:|----------------|---------|-------|
| 1 | 1 (Introduction) | One-to-one personal messaging | `personal_chats` / `chat_id` exist in SQL only; no DM UI or `send_message` path for personal chats. |
| 2 | 2.1.3 | Persistent login across browser restarts | `keep_signed_in` is stored in session state but not wired to long-lived auth tokens or cookies. |
| 3 | 2.1.4 | Working password reset flow | Forgot-password dialog always reports success; no reset token, email, or password update from reset. |
| 4 | 2.2.2–2.2.3 | AFK idle and multi-tab presence | `update_presence` exists but is never called from the app; no per-tab activity or 1-minute idle detection. |
| 5 | 2.2.4 | Session list shows IP details | `create_session` supports `ip_address`, but login never passes client IP; sessions UI shows user agent only. |
| 6 | 2.2.4 / 2.1.3 | Admin sign-out clears server session | `pages/admin.py` sign-out clears Streamlit state but does not `delete_session` in `user_sessions`. |
| 7 | 2.3.2 | Friend request from room roster | Friend requests are only from the Contacts dialog, not from the room members panel. |
| 8 | 2.3.5–2.3.6 | DM ban rules and frozen history | User bans and friendship rules are partly in SQL/services, but personal messaging is absent so freeze/read-only DM history is N/A. |
| 9 | 2.5.1 | Personal dialogs same as room chat | No end-to-end personal thread UI, attachments, or parity with room messaging. |
| 10 | 2.5.2 / 2.6.1 | Arbitrary file types in messages | Composer `file_uploader` is image types only; no general file upload path. |
| 11 | 2.6.2 | Paste-to-attach in composer | Only explicit file picker; no clipboard paste handling. |
| 12 | 2.6.3 | Optional attachment comment | `attachments.comment` column unused in compose/send UI. |
| 13 | 2.6.4 | Gated download for attachments | Files are inlined as base64 in the UI; no separate authorized download endpoint. |
| 14 | 2.6.5 / 3.4 | Files on disk under size policy | Attachments stored in SQLite (`data` BLOB), not local filesystem tree; 20 MB non-image cap not enforced. |
| 15 | 2.7.1 / 4.4 | Unread badges on rooms and contacts | No read receipts or unread counts in schema or sidebar. |
| 16 | 2.7.2 / 3.2 | Low-latency presence and delivery | Streamlit request/rerun model; no WebSockets or push for sub-2s presence / sub-3s fan-out. |
| 17 | 3.1 | Proven 300-user concurrency | No load tests; single-process Streamlit app is not validated for 300 simultaneous interactive users. |
| 18 | 3.2 | Ten-thousand-message room usability | Pagination is “load older” batches only; not validated for performance at 10k+ messages. |
| 19 | 4.1.1 | Rooms list on the right | Spec: rooms/contacts right; `user.py` uses a **left** column for rooms and contacts, right for members. |
| 20 | 4.2 | Autoscroll respects user scroll position | A generic scroll-to-bottom script is injected; does not implement “only if already at bottom” behavior reliably. |
| 21 | 4.3 | Emoji picker in composer | Multiline text allows pasted emoji; no in-UI emoji picker as in typical chat clients. |
| 22 | 5 (Notes) | Offline only when all tabs closed | Depends on 2.2.2–2.2.3; without tab-aware presence, offline semantics do not match the clarification doc. |