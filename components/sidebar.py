import streamlit as st
from services.room import get_user_rooms
from utils.session import current_user_id


def render_sidebar(conn) -> int | None:
    """Render left sidebar; returns selected room_id or None."""
    with st.sidebar:
        st.text_input("Search", key="room_search")
        rooms = get_user_rooms(conn, current_user_id())
        selected = None
        with st.expander("Rooms", expanded=True):
            for r in rooms:
                if st.button(r["name"], key=f"room_{r['id']}"):
                    selected = r["id"]
    return selected
