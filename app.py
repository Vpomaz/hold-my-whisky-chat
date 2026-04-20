import streamlit as st
from utils.db import get_db
from utils.session import require_auth

st.set_page_config(
    page_title="Hold My Whisky Chat",
    page_icon="🥃",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth()

st.write("Chat UI goes here")
