import streamlit as st

st.set_page_config(
    page_title="Hold My Whisky Chat",
    page_icon="🥃",
    layout="wide",
)

_about = st.Page("pages/about.py", title="About",   icon="🥃")
_login = st.Page("pages/login.py", title="Sign In", icon="🔑")
_user  = st.Page("pages/user.py",  title="Chat",    icon="💬")
_admin = st.Page("pages/admin.py", title="Admin",   icon="🛠️")

if "user_id" not in st.session_state:
    pg = st.navigation([_about, _login], position="sidebar")
else:
    # hide the sidebar completely after authentication
    st.markdown(
        """<style>
            section[data-testid="stSidebar"]      { display: none !important; }
            [data-testid="collapsedControl"]       { display: none !important; }
        </style>""",
        unsafe_allow_html=True,
    )
    role = st.session_state.get("role", "user")
    pg = st.navigation([_admin if role == "admin" else _user], position="hidden")

pg.run()
