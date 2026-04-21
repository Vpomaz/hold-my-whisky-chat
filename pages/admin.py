import streamlit as st

from components.navigation import nav_admin
from services.room import (
    ban_member,
    delete_room_by_id,
    get_all_rooms,
    get_room,
    get_room_bans,
    get_room_invitations,
    get_room_members,
    make_admin,
    remove_admin,
    send_invitation,
    unban_member,
    update_room,
)
from utils.db import get_db

conn = get_db()
current_user_id: int = st.session_state["user_id"]

all_rooms = get_all_rooms(conn)
action = nav_admin(all_rooms)

if action == "signout":
    st.session_state.clear()
    st.rerun()

if not all_rooms:
    st.info("No rooms exist yet.")
    st.stop()

selected_name = st.session_state.get("admin_selected_room")
room = next((r for r in all_rooms if r["name"] == selected_name), all_rooms[0])
room_id: int = room["id"]

st.subheader(f"# {room['name']}")

tab_members, tab_admins, tab_banned, tab_invitations, tab_settings = st.tabs(
    ["Members", "Admins", "Banned users", "Invitations", "Settings"]
)

# ── Members ──────────────────────────────────────────────────────────────────
with tab_members:
    search = st.text_input("Search member", placeholder="Search by username…", key="member_search")
    members = get_room_members(conn, room_id)
    if search:
        members = [m for m in members if search.lower() in m["username"].lower()]

    if not members:
        st.caption("No members found.")
    else:
        PRESENCE_ICON = {"online": "🟢", "afk": "🟡", "offline": "⚫"}
        hcols = st.columns([3, 2, 2, 5])
        for label, col in zip(["**Username**", "**Status**", "**Role**", "**Actions**"], hcols):
            col.markdown(label)

        for m in members:
            cols = st.columns([3, 2, 2, 5])
            icon = PRESENCE_ICON.get(m["presence"], "⚫")
            cols[0].write(m["username"])
            cols[1].write(f"{icon} {m['presence']}")
            cols[2].write(m["role"])

            with cols[3]:
                if m["role"] == "owner":
                    st.caption("—")
                elif m["role"] == "admin":
                    a, b = st.columns(2)
                    if a.button("Remove admin", key=f"rm_adm_{m['id']}"):
                        remove_admin(conn, room_id, m["id"])
                        st.rerun()
                    if b.button("Ban", key=f"ban_adm_{m['id']}", type="primary"):
                        ban_member(conn, room_id, m["id"], current_user_id)
                        st.rerun()
                else:
                    a, b, c = st.columns(3)
                    if a.button("Make admin", key=f"mk_adm_{m['id']}"):
                        make_admin(conn, room_id, m["id"])
                        st.rerun()
                    if b.button("Ban", key=f"ban_mem_{m['id']}", type="primary"):
                        ban_member(conn, room_id, m["id"], current_user_id)
                        st.rerun()
                    if c.button("Remove", key=f"rm_mem_{m['id']}", type="primary"):
                        ban_member(conn, room_id, m["id"], current_user_id)
                        st.rerun()

# ── Admins ───────────────────────────────────────────────────────────────────
with tab_admins:
    members = get_room_members(conn, room_id)
    admins = [m for m in members if m["role"] in ("admin", "owner")]
    admin_names = ", ".join(a["username"] for a in admins)
    st.caption(f"Current admins: {admin_names}")
    st.write("")

    for a in admins:
        cols = st.columns([5, 2])
        if a["role"] == "owner":
            cols[0].write(f"**{a['username']}** — owner (cannot lose admin rights)")
        else:
            cols[0].write(a["username"])
            if cols[1].button("Remove admin", key=f"tab_rm_adm_{a['id']}"):
                remove_admin(conn, room_id, a["id"])
                st.rerun()

# ── Banned users ─────────────────────────────────────────────────────────────
with tab_banned:
    bans = get_room_bans(conn, room_id)
    if not bans:
        st.caption("No banned users.")
    else:
        hcols = st.columns([3, 3, 3, 2])
        for label, col in zip(
            ["**Username**", "**Banned by**", "**Date/time**", "**Actions**"], hcols
        ):
            col.markdown(label)

        for ban in bans:
            cols = st.columns([3, 3, 3, 2])
            cols[0].write(ban["banned_username"])
            cols[1].write(ban["banned_by_username"])
            cols[2].write(ban["banned_at"][:16])
            if cols[3].button("Unban", key=f"unban_{ban['user_id']}"):
                unban_member(conn, room_id, ban["user_id"])
                st.rerun()

# ── Invitations ───────────────────────────────────────────────────────────────
with tab_invitations:
    pending = get_room_invitations(conn, room_id)
    if pending:
        st.markdown("**Pending invitations:**")
        for inv in pending:
            st.write(
                f"→ **{inv['invitee_username']}** "
                f"(invited by {inv['inviter_username']} on {inv['created_at'][:10]})"
            )
        st.divider()

    with st.form("invite_form"):
        invite_username = st.text_input("Invite by username")
        if st.form_submit_button("Send invite"):
            if invite_username.strip():
                ok, msg = send_invitation(conn, room_id, current_user_id, invite_username.strip())
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

# ── Settings ──────────────────────────────────────────────────────────────────
with tab_settings:
    room_detail = get_room(conn, room_id)

    with st.form("settings_form"):
        new_name = st.text_input("Room name", value=room_detail["name"])
        new_desc = st.text_area("Description", value=room_detail["description"])
        new_vis = st.radio(
            "Visibility",
            options=["public", "private"],
            index=0 if room_detail["visibility"] == "public" else 1,
            horizontal=True,
        )
        if st.form_submit_button("Save changes"):
            ok, msg = update_room(conn, room_id, new_name, new_desc, new_vis)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.divider()

    @st.dialog("Confirm deletion")
    def _confirm_delete() -> None:
        st.warning(
            f"Delete **#{room_detail['name']}**? "
            "All messages and files will be permanently removed."
        )
        col_yes, col_no = st.columns(2)
        if col_yes.button("Yes, delete", type="primary", use_container_width=True):
            delete_room_by_id(conn, room_id)
            st.session_state.pop("admin_selected_room", None)
            st.rerun()
        if col_no.button("Cancel", use_container_width=True):
            st.rerun()

    if st.button("Delete room", type="primary", key="open_delete_dialog"):
        _confirm_delete()
