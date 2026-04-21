import streamlit as st

LOGO = "🥃 Hold My Whisky"


def nav_login() -> str | None:
    """Top bar for login.py. Returns 'signin' or 'register' on button click."""
    col_logo, col_spacer, col_signin, col_register = st.columns([3, 5, 1, 1])
    with col_logo:
        st.markdown(f"### {LOGO}")
    with col_signin:
        if st.button("Sign in", use_container_width=True):
            return "signin"
    with col_register:
        if st.button("Register", type="primary", use_container_width=True):
            return "register"
    st.divider()
    return None


def nav_user() -> str | None:
    """Top bar for user.py. Returns the name of the clicked action or None."""
    col_logo, col_pub, col_priv, col_contacts, col_sessions, col_profile, col_signout = st.columns(
        [3, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5]
    )
    action = None
    with col_logo:
        st.markdown(f"### {LOGO}")
    with col_pub:
        if st.button("Public Rooms", use_container_width=True):
            action = "public_rooms"
    with col_priv:
        if st.button("Private Rooms", use_container_width=True):
            action = "private_rooms"
    with col_contacts:
        if st.button("Contacts", use_container_width=True):
            action = "contacts"
    with col_sessions:
        if st.button("Sessions", use_container_width=True):
            action = "sessions"
    with col_profile:
        if st.button("Profile", use_container_width=True):
            action = "profile"
    with col_signout:
        if st.button("Sign out", use_container_width=True):
            action = "signout"
    st.divider()
    return action


def nav_admin() -> str | None:
    """Top bar for admin.py. Returns selected room name or 'signout'."""
    col_logo, col_room, col_spacer, col_signout = st.columns([3, 4, 3, 1])
    action = None
    with col_logo:
        st.markdown(f"### {LOGO}")
    with col_room:
        rooms = st.session_state.get("admin_rooms", [])
        st.selectbox("Manage room", options=rooms, key="admin_selected_room")
    with col_signout:
        if st.button("Sign out", use_container_width=True):
            action = "signout"
    st.divider()
    return action
