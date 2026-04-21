import base64

import streamlit as st

from components.navigation import nav_user
from services.auth import change_password, delete_account, update_email
from services.friend import (
    accept_request,
    block_user,
    decline_request,
    get_blocked_users,
    get_friends,
    get_pending_incoming,
    get_pending_outgoing,
    remove_friend,
    send_friend_request,
    unblock_user,
)
from services.message import delete_message, edit_message, send_message
from services.room import (
    ban_member,
    create_room,
    delete_room_by_id,
    get_member_role,
    get_public_rooms,
    get_room,
    get_room_bans,
    get_room_invitations,
    get_room_members,
    get_user_rooms,
    is_banned_from_room,
    join_room,
    leave_room,
    make_admin,
    remove_admin,
    send_invitation,
    unban_member,
    update_room,
)
from services.session_mgr import delete_session, get_sessions
from utils.db import get_db

# ── Bootstrap ─────────────────────────────────────────────────────────────────
conn = get_db()
uid: int = st.session_state["user_id"]
uname: str = st.session_state["username"]

st.session_state.setdefault("current_room_id", None)
st.session_state.setdefault("reply_to_id", None)
st.session_state.setdefault("reply_to_author", None)
st.session_state.setdefault("reply_to_preview", None)
st.session_state.setdefault("editing_msg_id", None)

room_id: int | None = st.session_state["current_room_id"]

# Reset pagination when room changes
if st.session_state.get("_prev_room") != room_id:
    st.session_state["_prev_room"] = room_id
    st.session_state["_msg_limit"] = 50

# ── Message display helper ────────────────────────────────────────────────────
PRESENCE_ICON = {"online": "●", "afk": "◐", "offline": "○"}


def _display_message(msg: dict, is_own: bool, is_mod: bool) -> None:
    ts = msg["created_at"][11:16]
    edited_note = "  *(edited)*" if msg["edited_at"] else ""

    with st.chat_message("user" if is_own else msg["author"]):
        # Quoted reply
        if msg["reply_to_id"] and msg["reply_author"]:
            preview = (msg["reply_content"] or "")[:80]
            st.markdown(
                f"<div style='border-left:3px solid #888;padding-left:8px;"
                f"color:#888;margin-bottom:4px'>↩ <b>{msg['reply_author']}</b>: {preview}</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"**{msg['author']}** <span style='color:#888;font-size:0.8em'>{ts}{edited_note}</span>",
            unsafe_allow_html=True,
        )
        st.write(msg["content"])

        # Attachments (images stored as base64)
        attachments = conn.execute(
            "SELECT original_name, data, mime_type, file_size FROM attachments WHERE message_id=?",
            (msg["id"],),
        ).fetchall()
        for att in attachments:
            if att["data"] and att["mime_type"] and att["mime_type"].startswith("image/"):
                st.image(
                    f"data:{att['mime_type']};base64,{att['data']}",
                    caption=att["original_name"],
                    use_container_width=False,
                    width=320,
                )
            elif att["data"]:
                size_kb = att["file_size"] // 1024 or 1
                st.caption(f"📎 {att['original_name']} ({size_kb} KB)")

        # Action row
        btn_cols = st.columns([1, 1, 1, 6])
        if btn_cols[0].button("↩", key=f"reply_{msg['id']}", help="Reply"):
            st.session_state["reply_to_id"] = msg["id"]
            st.session_state["reply_to_author"] = msg["author"]
            st.session_state["reply_to_preview"] = (msg["content"] or "")[:50]
            st.rerun()
        if is_own and btn_cols[1].button("✏", key=f"edit_{msg['id']}", help="Edit"):
            st.session_state["editing_msg_id"] = msg["id"]
            st.rerun()
        if (is_own or is_mod) and btn_cols[2].button("🗑", key=f"del_{msg['id']}", help="Delete"):
            delete_message(conn, msg["id"])
            st.rerun()

    # Inline edit form (outside the chat_message bubble)
    if st.session_state.get("editing_msg_id") == msg["id"]:
        with st.form(f"edit_form_{msg['id']}"):
            new_text = st.text_area("Edit message", value=msg["content"], height=80)
            col_s, col_c = st.columns(2)
            if col_s.form_submit_button("Save", type="primary"):
                edit_message(conn, msg["id"], uid, new_text.strip())
                st.session_state["editing_msg_id"] = None
                st.rerun()
            if col_c.form_submit_button("Cancel"):
                st.session_state["editing_msg_id"] = None
                st.rerun()


# ── Dialog: create room ───────────────────────────────────────────────────────
@st.dialog("Create room")
def dlg_create_room() -> None:
    with st.form("cr_form"):
        name = st.text_input("Room name")
        desc = st.text_area("Description", height=80)
        vis = st.radio("Visibility", ["public", "private"], horizontal=True)
        if st.form_submit_button("Create", type="primary"):
            if name.strip():
                try:
                    new_id = create_room(conn, name.strip(), desc.strip(), vis, uid)
                    st.session_state["current_room_id"] = new_id
                    st.session_state["_msg_limit"] = 50
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
            else:
                st.error("Room name is required")


# ── Dialog: invite user ───────────────────────────────────────────────────────
@st.dialog("Invite user")
def dlg_invite_user(the_room_id: int) -> None:
    with st.form("inv_form"):
        invitee = st.text_input("Username")
        if st.form_submit_button("Send invite", type="primary"):
            if invitee.strip():
                ok, msg = send_invitation(conn, the_room_id, uid, invitee.strip())
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)


# ── Dialog: manage room ───────────────────────────────────────────────────────
@st.dialog("Manage room", width="large")
def dlg_manage_room(the_room_id: int) -> None:
    room_d = get_room(conn, the_room_id)
    if not room_d:
        st.error("Room not found")
        return

    st.subheader(f"# {room_d['name']}")
    tab_m, tab_a, tab_b, tab_i, tab_s = st.tabs(
        ["Members", "Admins", "Banned users", "Invitations", "Settings"]
    )

    with tab_m:
        q = st.text_input("Search member", key="mgr_search")
        mems = get_room_members(conn, the_room_id)
        if q:
            mems = [m for m in mems if q.lower() in m["username"].lower()]
        hc = st.columns([3, 2, 2, 5])
        for lbl, col in zip(["**Username**", "**Status**", "**Role**", "**Actions**"], hc):
            col.markdown(lbl)
        for m in mems:
            cols = st.columns([3, 2, 2, 5])
            cols[0].write(m["username"])
            cols[1].write(f"{PRESENCE_ICON.get(m['presence'], '○')} {m['presence']}")
            cols[2].write(m["role"])
            with cols[3]:
                if m["role"] == "owner":
                    st.caption("—")
                elif m["role"] == "admin":
                    a, b = st.columns(2)
                    if a.button("Remove admin", key=f"mgr_rm_adm_{m['id']}"):
                        remove_admin(conn, the_room_id, m["id"])
                        st.rerun()
                    if b.button("Ban", key=f"mgr_ban_adm_{m['id']}", type="primary"):
                        ban_member(conn, the_room_id, m["id"], uid)
                        st.rerun()
                else:
                    a, b, c = st.columns(3)
                    if a.button("Make admin", key=f"mgr_mk_{m['id']}"):
                        make_admin(conn, the_room_id, m["id"])
                        st.rerun()
                    if b.button("Ban", key=f"mgr_ban_{m['id']}", type="primary"):
                        ban_member(conn, the_room_id, m["id"], uid)
                        st.rerun()
                    if c.button("Remove", key=f"mgr_rm_{m['id']}", type="primary"):
                        ban_member(conn, the_room_id, m["id"], uid)
                        st.rerun()

    with tab_a:
        mems = get_room_members(conn, the_room_id)
        admins = [m for m in mems if m["role"] in ("admin", "owner")]
        st.caption(f"Current admins: {', '.join(a['username'] for a in admins)}")
        st.write("")
        for a in admins:
            cols = st.columns([5, 2])
            if a["role"] == "owner":
                cols[0].write(f"**{a['username']}** — owner (cannot lose admin rights)")
            else:
                cols[0].write(a["username"])
                if cols[1].button("Remove admin", key=f"mgr_tab_rm_{a['id']}"):
                    remove_admin(conn, the_room_id, a["id"])
                    st.rerun()

    with tab_b:
        bans = get_room_bans(conn, the_room_id)
        if not bans:
            st.caption("No banned users.")
        else:
            hc = st.columns([3, 3, 3, 2])
            for lbl, col in zip(["**Username**", "**Banned by**", "**Date/time**", "**Actions**"], hc):
                col.markdown(lbl)
            for ban in bans:
                cols = st.columns([3, 3, 3, 2])
                cols[0].write(ban["banned_username"])
                cols[1].write(ban["banned_by_username"])
                cols[2].write(ban["banned_at"][:16])
                if cols[3].button("Unban", key=f"mgr_unban_{ban['user_id']}"):
                    unban_member(conn, the_room_id, ban["user_id"])
                    st.rerun()

    with tab_i:
        pending = get_room_invitations(conn, the_room_id)
        if pending:
            st.markdown("**Pending:**")
            for inv in pending:
                st.write(
                    f"→ **{inv['invitee_username']}** "
                    f"invited by {inv['inviter_username']} on {inv['created_at'][:10]}"
                )
            st.divider()
        with st.form("mgr_invite"):
            u = st.text_input("Invite by username")
            if st.form_submit_button("Send invite"):
                if u.strip():
                    ok, msg = send_invitation(conn, the_room_id, uid, u.strip())
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    with tab_s:
        with st.form("mgr_settings"):
            nn = st.text_input("Room name", value=room_d["name"])
            nd = st.text_area("Description", value=room_d["description"])
            nv = st.radio(
                "Visibility",
                ["public", "private"],
                index=0 if room_d["visibility"] == "public" else 1,
                horizontal=True,
            )
            if st.form_submit_button("Save changes"):
                ok, msg = update_room(conn, the_room_id, nn, nd, nv)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        st.divider()
        if st.button("Delete room", type="primary", key="mgr_del_room"):
            delete_room_by_id(conn, the_room_id)
            st.session_state["current_room_id"] = None
            st.rerun()


# ── Dialog: public rooms ──────────────────────────────────────────────────────
@st.dialog("Public Rooms", width="large")
def dlg_public_rooms() -> None:
    st.caption("Browse and join public chat rooms (section 2.4.3).")
    search = st.text_input("Search rooms", placeholder="Search by name…", key="pub_dlg_search")
    all_pub = get_public_rooms(conn, search=search)
    joined_ids = {r["id"] for r in get_user_rooms(conn, uid)}

    if not all_pub:
        st.info("No public rooms found.")
        return

    hcols = st.columns([4, 4, 2, 2])
    for lbl, col in zip(["**Room**", "**Description**", "**Members**", "**Action**"], hcols):
        col.markdown(lbl)

    for pr in all_pub:
        cols = st.columns([4, 4, 2, 2])
        cols[0].write(f"**#{pr['name']}**")
        cols[1].caption((pr["description"] or "")[:55] or "—")
        cols[2].write(str(pr["member_count"]))
        banned = is_banned_from_room(conn, pr["id"], uid)
        if banned:
            cols[3].caption("Banned")
        elif pr["id"] in joined_ids:
            if cols[3].button("Open →", key=f"dlg_pub_open_{pr['id']}", use_container_width=True):
                st.session_state["current_room_id"] = pr["id"]
                st.session_state["_msg_limit"] = 50
                st.rerun()
        else:
            if cols[3].button("Join", key=f"dlg_pub_join_{pr['id']}", type="primary", use_container_width=True):
                join_room(conn, pr["id"], uid)
                st.session_state["current_room_id"] = pr["id"]
                st.session_state["_msg_limit"] = 50
                st.rerun()


# ── Dialog: private rooms ─────────────────────────────────────────────────────
@st.dialog("Private Rooms", width="large")
def dlg_private_rooms() -> None:
    st.caption("Private rooms are only accessible by invitation (section 2.4.4).")
    tab_mine, tab_invites = st.tabs(["My Private Rooms", "Pending Invitations"])

    with tab_mine:
        prv = [r for r in get_user_rooms(conn, uid) if r["visibility"] == "private"]
        if not prv:
            st.info("You are not a member of any private room.")
        for r in prv:
            cols = st.columns([5, 2, 2])
            cols[0].write(f"**#{r['name']}**  ·  *{r['role']}*")
            if cols[1].button("Open →", key=f"prv_open_{r['id']}"):
                st.session_state["current_room_id"] = r["id"]
                st.session_state["_msg_limit"] = 50
                st.rerun()
            if r["role"] != "owner":
                if cols[2].button("Leave", key=f"prv_leave_{r['id']}"):
                    leave_room(conn, r["id"], uid)
                    if st.session_state.get("current_room_id") == r["id"]:
                        st.session_state["current_room_id"] = None
                    st.rerun()

    with tab_invites:
        invites = conn.execute(
            """
            SELECT ri.id, r.name AS room_name, r.id AS room_id,
                   u.username AS inviter_username, ri.created_at
            FROM room_invitations ri
            JOIN rooms r ON r.id = ri.room_id
            JOIN users u ON u.id = ri.inviter_id
            WHERE ri.invitee_id=?
            ORDER BY ri.created_at DESC
            """,
            (uid,),
        ).fetchall()
        if not invites:
            st.info("No pending invitations.")
        for inv in invites:
            cols = st.columns([4, 3, 2, 2])
            cols[0].write(f"**#{inv['room_name']}**")
            cols[1].caption(f"from **{inv['inviter_username']}** on {inv['created_at'][:10]}")
            if cols[2].button("Accept", key=f"inv_acc_{inv['id']}", type="primary"):
                join_room(conn, inv["room_id"], uid)
                conn.execute("DELETE FROM room_invitations WHERE id=?", (inv["id"],))
                conn.commit()
                st.session_state["current_room_id"] = inv["room_id"]
                st.session_state["_msg_limit"] = 50
                st.rerun()
            if cols[3].button("Decline", key=f"inv_dec_{inv['id']}"):
                conn.execute("DELETE FROM room_invitations WHERE id=?", (inv["id"],))
                conn.commit()
                st.rerun()


# ── Dialog: contacts ──────────────────────────────────────────────────────────
@st.dialog("Contacts", width="large")
def dlg_contacts() -> None:
    tab_friends, tab_requests, tab_send, tab_blocked = st.tabs(
        ["Friends", "Requests", "Add friend", "Blocked"]
    )

    with tab_friends:
        friends = get_friends(conn, uid)
        if not friends:
            st.info("Your friend list is empty.")
        else:
            PICON = {"online": "●", "afk": "◐", "offline": "○"}
            hcols = st.columns([4, 2, 2, 2])
            for lbl, col in zip(["**Username**", "**Status**", "**Remove**", "**Block**"], hcols):
                col.markdown(lbl)
            for f in friends:
                cols = st.columns([4, 2, 2, 2])
                cols[0].write(f['username'])
                cols[1].write(f"{PICON.get(f['presence'], '○')} {f['presence']}")
                if cols[2].button("Remove", key=f"fr_rm_{f['friend_id']}"):
                    remove_friend(conn, uid, f["friend_id"])
                    st.rerun()
                if cols[3].button("Block", key=f"fr_blk_{f['friend_id']}", type="primary"):
                    block_user(conn, uid, f["username"])
                    st.rerun()

    with tab_requests:
        incoming = get_pending_incoming(conn, uid)
        outgoing = get_pending_outgoing(conn, uid)

        st.markdown("**Incoming requests**")
        if not incoming:
            st.caption("No incoming requests.")
        for req in incoming:
            cols = st.columns([4, 3, 2, 2])
            cols[0].write(f"**{req['requester_username']}**")
            cols[1].caption(req["message"] or "")
            if cols[2].button("Accept", key=f"req_acc_{req['id']}", type="primary"):
                ok, msg = accept_request(conn, req["id"], uid)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            if cols[3].button("Decline", key=f"req_dec_{req['id']}"):
                decline_request(conn, req["id"])
                st.rerun()

        st.markdown("---")
        st.markdown("**Sent requests**")
        if not outgoing:
            st.caption("No outgoing requests.")
        for req in outgoing:
            cols = st.columns([5, 3, 2])
            cols[0].write(f"→ **{req['addressee_username']}**")
            cols[1].caption(req["created_at"][:10])
            if cols[2].button("Cancel", key=f"req_can_{req['id']}"):
                decline_request(conn, req["id"])
                st.rerun()

    with tab_send:
        with st.form("add_friend_form"):
            target = st.text_input("Username")
            msg = st.text_input("Message (optional)")
            if st.form_submit_button("Send request", type="primary"):
                if target.strip():
                    ok, text = send_friend_request(conn, uid, target.strip(), msg.strip())
                    if ok:
                        st.success(text)
                        st.rerun()
                    else:
                        st.error(text)
                else:
                    st.error("Username is required")

    with tab_blocked:
        blocked = get_blocked_users(conn, uid)
        if not blocked:
            st.info("You have not blocked anyone.")
        else:
            st.caption("Blocked users cannot contact you and you cannot contact them.")
            for b in blocked:
                cols = st.columns([5, 3, 2])
                cols[0].write(b["username"])
                cols[1].caption(b["created_at"][:10])
                if cols[2].button("Unblock", key=f"unblk_{b['banned_id']}"):
                    unblock_user(conn, uid, b["banned_id"])
                    st.rerun()


# ── Dialog: sessions ──────────────────────────────────────────────────────────
@st.dialog("Active Sessions", width="large")
def dlg_sessions() -> None:
    st.caption("All browser sessions for your account (section 2.2.4).")
    sessions = get_sessions(conn, uid)
    current_sid = st.session_state.get("session_id")

    if not sessions:
        st.info("No active sessions recorded. Sessions are created on sign-in.")
        return

    PICON = {"online": "🟢", "afk": "🟡", "offline": "⚫"}
    hcols = st.columns([4, 3, 2, 2])
    for lbl, col in zip(["**Browser / Agent**", "**Last seen**", "**Status**", "**Action**"], hcols):
        col.markdown(lbl)

    for s in sessions:
        is_current = s["id"] == current_sid
        cols = st.columns([4, 3, 2, 2])
        agent = (s["user_agent"] or "Unknown")[:50]
        label = f"{agent}  *(this browser)*" if is_current else agent
        cols[0].write(label)
        cols[1].caption(s["last_seen"][:16])
        cols[2].write(f"{PICON.get(s['presence'], '⚫')} {s['presence']}")
        if is_current:
            cols[3].caption("—")
        else:
            if cols[3].button("Log out", key=f"ses_del_{s['id']}", type="primary"):
                delete_session(conn, s["id"])
                st.rerun()


# ── Dialog: profile ───────────────────────────────────────────────────────────
@st.dialog("Profile & Settings", width="large")
def dlg_profile() -> None:
    user = conn.execute(
        "SELECT email, username FROM users WHERE id=?", (uid,)
    ).fetchone()

    st.markdown(f"**Username:** `{user['username']}`  *(immutable)*")
    st.markdown(f"**Email:** `{user['email']}`")
    st.divider()

    tab_email, tab_pass, tab_del = st.tabs(["Change email", "Change password", "Delete account"])

    with tab_email:
        with st.form("email_form"):
            new_email = st.text_input("New email address")
            if st.form_submit_button("Update email", type="primary"):
                if new_email.strip():
                    ok, msg = update_email(conn, uid, new_email.strip())
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Email is required")

    with tab_pass:
        with st.form("pass_form"):
            old_p = st.text_input("Current password", type="password")
            new_p = st.text_input("New password", type="password")
            confirm_p = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Change password", type="primary"):
                if new_p != confirm_p:
                    st.error("Passwords do not match")
                elif len(new_p) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    ok, msg = change_password(conn, uid, old_p, new_p)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

    with tab_del:
        st.warning(
            "**Deleting your account is permanent.** "
            "All rooms you own — and their messages and files — will be deleted. "
            "You will be removed from all other rooms."
        )
        with st.form("del_form"):
            confirm_txt = st.text_input(f"Type **{user['username']}** to confirm")
            if st.form_submit_button("Delete my account", type="primary"):
                if confirm_txt == user["username"]:
                    delete_account(conn, uid)
                    st.session_state.clear()
                    st.rerun()
                else:
                    st.error("Username does not match")


# ── Nav bar ───────────────────────────────────────────────────────────────────
action = nav_user()
if action == "signout":
    if st.session_state.get("session_id"):
        delete_session(conn, st.session_state["session_id"])
    st.session_state.clear()
    st.rerun()
elif action == "public_rooms":
    dlg_public_rooms()
elif action == "private_rooms":
    dlg_private_rooms()
elif action == "contacts":
    dlg_contacts()
elif action == "sessions":
    dlg_sessions()
elif action == "profile":
    dlg_profile()

# ── Row 1: three-column layout ────────────────────────────────────────────────
row1 = st.container()
row2 = st.container()

with row1:
    col_left, col_mid, col_right = st.columns([2, 5, 2], gap="small")

    # ── Left: sidebar ─────────────────────────────────────────────────────────
    with col_left:
        search = st.text_input(
            "Search", placeholder="🔍 Filter rooms…", label_visibility="collapsed"
        )

        my_rooms = get_user_rooms(conn, uid)
        if search:
            my_rooms = [r for r in my_rooms if search.lower() in r["name"].lower()]

        pub_joined = [r for r in my_rooms if r["visibility"] == "public"]
        prv_joined = [r for r in my_rooms if r["visibility"] == "private"]

        with st.expander("**▶ Public Rooms**", expanded=True):
            if pub_joined:
                for r in pub_joined:
                    active = r["id"] == room_id
                    if st.button(
                        f"# {r['name']}",
                        key=f"pub_{r['id']}",
                        use_container_width=True,
                        type="primary" if active else "secondary",
                    ):
                        st.session_state["current_room_id"] = r["id"]
                        st.session_state["reply_to_id"] = None
                        st.session_state["_msg_limit"] = 50
                        st.rerun()
            else:
                st.caption("No public rooms joined")

        with st.expander("**▶ Private Rooms**", expanded=True):
            if prv_joined:
                for r in prv_joined:
                    active = r["id"] == room_id
                    if st.button(
                        f"# {r['name']}",
                        key=f"prv_{r['id']}",
                        use_container_width=True,
                        type="primary" if active else "secondary",
                    ):
                        st.session_state["current_room_id"] = r["id"]
                        st.session_state["reply_to_id"] = None
                        st.session_state["_msg_limit"] = 50
                        st.rerun()
            else:
                st.caption("No private rooms joined")

        st.markdown("---")
        st.markdown("**CONTACTS**")
        contacts = conn.execute(
            """
            SELECT u.id, u.username,
                   COALESCE(
                       CASE MAX(
                           CASE s.presence WHEN 'online' THEN 3 WHEN 'afk' THEN 2 ELSE 1 END
                       )
                       WHEN 3 THEN 'online' WHEN 2 THEN 'afk' ELSE 'offline' END,
                       'offline'
                   ) AS presence
            FROM friendships f
            JOIN users u ON u.id = CASE WHEN f.requester_id=? THEN f.addressee_id ELSE f.requester_id END
            LEFT JOIN user_sessions s ON s.user_id = u.id
            WHERE (f.requester_id=? OR f.addressee_id=?) AND f.status='accepted'
              AND u.deleted_at IS NULL
            GROUP BY u.id, u.username
            ORDER BY u.username
            """,
            (uid, uid, uid),
        ).fetchall()

        if contacts:
            for c in contacts:
                icon = PRESENCE_ICON.get(c["presence"], "○")
                st.write(f"{icon} {c['username']}")
        else:
            st.caption("No contacts yet")

        st.markdown("---")
        if st.button("＋ Create room", use_container_width=True, type="primary"):
            dlg_create_room()

    # ── Middle: chat ──────────────────────────────────────────────────────────
    with col_mid:
        if not room_id:
            st.markdown("### 💬 Select a room to start chatting")
            st.caption("Join or open a room from the sidebar.")
            st.markdown("---")
            st.markdown("**Browse public rooms:**")
            pub_q = st.text_input("Search public rooms", placeholder="Type to search…", key="pub_search")
            all_pub = get_public_rooms(conn, search=pub_q)

            joined_ids = {r["id"] for r in get_user_rooms(conn, uid)}
            for pr in all_pub:
                cols = st.columns([6, 1])
                cols[0].write(f"**#{pr['name']}** — {pr['description']} · {pr['member_count']} members")
                banned = is_banned_from_room(conn, pr["id"], uid)
                if banned:
                    cols[1].caption("Banned")
                elif pr["id"] in joined_ids:
                    if cols[1].button("Open", key=f"open_{pr['id']}"):
                        st.session_state["current_room_id"] = pr["id"]
                        st.rerun()
                else:
                    if cols[1].button("Join", key=f"join_{pr['id']}", type="primary"):
                        join_room(conn, pr["id"], uid)
                        st.session_state["current_room_id"] = pr["id"]
                        st.rerun()
        else:
            room = get_room(conn, room_id)
            if not room:
                st.warning("Room not found.")
                st.session_state["current_room_id"] = None
            else:
                my_role = get_member_role(conn, room_id, uid)

                if not my_role:
                    st.subheader(f"# {room['name']}")
                    st.caption(room["description"])
                    banned = is_banned_from_room(conn, room_id, uid)
                    if banned:
                        st.error("You are banned from this room.")
                    elif room["visibility"] == "public":
                        if st.button("Join room", type="primary"):
                            join_room(conn, room_id, uid)
                            st.rerun()
                    else:
                        st.info("Private room — you need an invitation to join.")
                else:
                    st.subheader(f"# {room['name']}")
                    if room["description"]:
                        st.caption(room["description"])

                    # Message history
                    limit = st.session_state["_msg_limit"]
                    msgs = conn.execute(
                        """
                        SELECT m.id, m.content, m.created_at, m.edited_at, m.reply_to_id,
                               u.username AS author,
                               rm.content AS reply_content,
                               ru.username AS reply_author
                        FROM messages m
                        JOIN users u ON u.id = m.author_id
                        LEFT JOIN messages rm ON rm.id = m.reply_to_id
                        LEFT JOIN users ru ON ru.id = rm.author_id
                        WHERE m.room_id = ? AND m.deleted_at IS NULL
                        ORDER BY m.id DESC LIMIT ?
                        """,
                        (room_id, limit),
                    ).fetchall()
                    msgs = list(reversed(msgs))

                    total = conn.execute(
                        "SELECT COUNT(*) FROM messages WHERE room_id=? AND deleted_at IS NULL",
                        (room_id,),
                    ).fetchone()[0]

                    with st.container(height=460):
                        if total > limit:
                            if st.button(
                                f"⬆ Load older messages ({total - limit} more)",
                                use_container_width=True,
                            ):
                                st.session_state["_msg_limit"] += 50
                                st.rerun()

                        if not msgs:
                            st.caption("No messages yet — say something!")

                        is_mod = my_role in ("admin", "owner")
                        for msg in msgs:
                            _display_message(dict(msg), msg["author"] == uname, is_mod)

                    # Scroll to bottom
                    st.markdown(
                        "<script>"
                        "const el=window.parent.document.querySelector('[data-testid=\"stVerticalBlockBorderWrapper\"]');"
                        "if(el){el.scrollTop=el.scrollHeight;}"
                        "</script>",
                        unsafe_allow_html=True,
                    )

    # ── Right: room info panel ────────────────────────────────────────────────
    with col_right:
        if room_id:
            room = get_room(conn, room_id)
            if room:
                my_role = get_member_role(conn, room_id, uid)
                if my_role:
                    vis_label = "🔒 Private room" if room["visibility"] == "private" else "🌐 Public room"
                    st.markdown(f"**{vis_label}**")

                    members = get_room_members(conn, room_id)
                    owner = next((m for m in members if m["role"] == "owner"), None)
                    if owner:
                        st.write(f"Owner: **{owner['username']}**")

                    admins = [m for m in members if m["role"] in ("admin", "owner")]
                    if admins:
                        st.markdown("**Admins**")
                        for a in admins:
                            st.caption(f"— {a['username']}")

                    st.markdown(f"**Members ({len(members)})**")
                    for m in members:
                        icon = PRESENCE_ICON.get(m["presence"], "○")
                        suffix = (
                            " *(AFK)*" if m["presence"] == "afk"
                            else " *(offline)*" if m["presence"] == "offline"
                            else ""
                        )
                        st.write(f"{icon} {m['username']}{suffix}")

                    st.markdown("---")
                    if st.button("📨 Invite user", use_container_width=True):
                        dlg_invite_user(room_id)

                    if my_role in ("admin", "owner"):
                        if st.button("⚙ Manage room", use_container_width=True):
                            dlg_manage_room(room_id)

                    st.markdown("---")
                    if my_role != "owner":
                        if st.button("Leave room", use_container_width=True):
                            leave_room(conn, room_id, uid)
                            st.session_state["current_room_id"] = None
                            st.rerun()

# ── Row 2: message compose ────────────────────────────────────────────────────
with row2:
    if room_id:
        room = get_room(conn, room_id)
        my_role = get_member_role(conn, room_id, uid) if room else None

        if my_role:
            # Reply indicator
            if st.session_state.get("reply_to_id"):
                col_ri, col_rx = st.columns([11, 1])
                col_ri.info(
                    f"↩ Replying to **{st.session_state['reply_to_author']}**: "
                    f"_{st.session_state.get('reply_to_preview', '')}…_"
                )
                if col_rx.button("✕", key="clear_reply"):
                    st.session_state["reply_to_id"] = None
                    st.session_state["reply_to_author"] = None
                    st.session_state["reply_to_preview"] = None
                    st.rerun()

            with st.form("send_form", clear_on_submit=True):
                col_txt, col_send = st.columns([9, 1])
                with col_txt:
                    text = st.text_area(
                        "Message",
                        placeholder="Type a message… (Shift+Enter for new line)",
                        label_visibility="collapsed",
                        height=80,
                        max_chars=3072,
                    )
                    uploaded = st.file_uploader(
                        "📎 Attach image (max 3 MB)",
                        type=["jpg", "jpeg", "png", "gif", "webp"],
                        label_visibility="visible",
                    )
                with col_send:
                    st.write("")
                    st.write("")
                    st.write("")
                    submitted = st.form_submit_button("Send ➤", type="primary", use_container_width=True)

                if submitted:
                    content = (text or "").strip()
                    reply_id = st.session_state.get("reply_to_id")

                    if not content and not uploaded:
                        st.warning("Write something or attach an image.")
                    elif len(content.encode("utf-8")) > 3072:
                        st.error("Message exceeds 3 KB limit.")
                    elif uploaded and len(uploaded.getvalue()) > 3 * 1024 * 1024:
                        st.error("Image exceeds 3 MB limit.")
                    else:
                        if uploaded:
                            img_bytes = uploaded.getvalue()
                            b64 = base64.b64encode(img_bytes).decode()
                            msg_id = send_message(
                                conn, room_id, uid, content or f"[{uploaded.name}]", reply_id
                            )
                            conn.execute(
                                "INSERT INTO attachments "
                                "(message_id, original_name, stored_path, data, mime_type, file_size) "
                                "VALUES (?, ?, '', ?, ?, ?)",
                                (msg_id, uploaded.name, b64, uploaded.type, len(img_bytes)),
                            )
                            conn.commit()
                        else:
                            send_message(conn, room_id, uid, content, reply_id)

                        st.session_state["reply_to_id"] = None
                        st.session_state["reply_to_author"] = None
                        st.session_state["reply_to_preview"] = None
                        st.rerun()
