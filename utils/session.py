import streamlit as st


def redirect_by_role() -> None:
    """Re-run so app.py routes to the correct page for the current role."""
    st.rerun()


def current_user_id() -> int:
    return st.session_state["user_id"]


def current_username() -> str:
    return st.session_state["username"]


def current_user_role() -> str:
    return st.session_state.get("role", "user")
