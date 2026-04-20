# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**hold-my-whisky-chat** is a classic web-based chat application. The full specification is in [2026_04_18_AI_herders_jam_-_requirements_v3 1.txt](2026_04_18_AI_herders_jam_-_requirements_v3%201.txt).

**Submission requirement:** The project must be buildable and runnable via `docker compose up` from the repo root.

## Tech Stack

- **Backend/Frontend:** Python + Streamlit (no separate frontend framework)
- **Database:** SQLite only
- **Deployment:** Docker Compose

## Build & Run

```bash
docker compose up          # start all services
docker compose up --build  # rebuild images and start
```

## Key Functional Requirements

### Real-time constraints
- Message delivery: < 3 seconds
- Presence updates: < 2 seconds
- Support rooms with 10,000+ messages (infinite scroll)
- Scale: 300 simultaneous users, up to 1,000 members per room

### Presence logic (tricky)
A user is **online** if any browser tab is active, **AFK** if all tabs have been idle > 1 min, **offline** only when all tabs are closed. This requires cross-tab coordination (e.g., BroadcastChannel or shared worker).

### Access control rules
- Files are stored on local filesystem; access is tied to current room membership
- If a user loses room access, they immediately lose file/image access
- Files persist in storage even after the uploader loses access (only deleted when room is deleted)
- Personal messaging requires friendship with no active ban in either direction

### Room ban vs. remove
Removing a member from a room IS a ban — the user cannot rejoin until explicitly unbanned.

### Personal chats
Functionally identical to room chats (same message/attachment features), but fixed two-participant list and no admin roles.

## UI Layout (from wireframes)

Three-column layout:
- **Left sidebar:** search + accordion room/contact list with unread badges
- **Center:** message history (infinite scroll up) + message input (emoji, attach, reply-to)
- **Right sidebar:** room info, member list with presence indicators, admin controls

Admin actions are in modal dialogs with tabs: Members / Admins / Banned users / Invitations / Settings.

## Advanced Feature (optional)

Jabber/XMPP protocol support with federation between servers. Requires additional docker compose services and admin UI screens for connection dashboard and federation traffic stats. Load test: 50+ clients on server A ↔ 50+ clients on server B.

## File Size Limits
- Attachments: max 20 MB
- Images: max 3 MB
- Message text: max 3 KB (UTF-8)
