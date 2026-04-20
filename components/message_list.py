import streamlit as st


def render_message(msg: dict, is_own: bool = False) -> None:
    edited = " *(edited)*" if msg["edited_at"] else ""
    st.markdown(f"**{msg['author']}** `{msg['created_at']}`{edited}")
    if msg["reply_to_id"]:
        st.caption(f"↩ replying to message #{msg['reply_to_id']}")
    st.write(msg["content"])
