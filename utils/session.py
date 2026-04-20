import streamlit as st


def require_auth() -> None:
    """Redirect to login if no active session."""
    if "user_id" not in st.session_state:
        st.switch_page("pages/login.py")


def current_user_id() -> int:
    return st.session_state["user_id"]


def current_username() -> str:
    return st.session_state["username"]
