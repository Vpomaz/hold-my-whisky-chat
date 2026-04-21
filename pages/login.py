import streamlit as st
from components.navigation import nav_login
from services.auth import authenticate, register_user
from utils.db import get_db
from utils.session import redirect_by_role


@st.dialog("Forgot password")
def _forgot_password_modal() -> None:
    st.write("Enter your email to reset password")
    email = st.text_input("Email", key="reset_email")
    if st.button("Send reset link", type="primary", use_container_width=True):
        if email:
            st.success(f"Reset link sent to {email}")
        else:
            st.error("Please enter your email address.")


@st.dialog("Register")
def _register_modal() -> None:
    email = st.text_input("Email", key="reg_email")
    username = st.text_input("Username", key="reg_username")
    password = st.text_input("Password", type="password", key="reg_password")
    confirm = st.text_input("Confirm password", type="password", key="reg_confirm")

    if st.button("Create account", type="primary", use_container_width=True):
        if not all([email, username, password, confirm]):
            st.error("All fields are required.")
        elif password != confirm:
            st.error("Passwords do not match.")
        else:
            try:
                register_user(get_db(), email, username, password)
                st.success("Account created! You can now sign in.")
            except Exception:
                st.error("Email or username already taken.")


# ── nav bar ──────────────────────────────────────────────────────────────────
nav_action = nav_login()
if nav_action == "register":
    _register_modal()

# ── sign-in form ──────────────────────────────────────────────────────────────
_, col, _ = st.columns([1, 2, 1])
with col:
    st.subheader("Sign in")

    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")
    keep_signed_in = st.checkbox("Keep me signed in")

    if st.button("Sign in", type="primary", use_container_width=True):
        user = authenticate(get_db(), email, password)
        if user:
            st.session_state["user_id"] = user["id"]
            st.session_state["username"] = user["username"]
            st.session_state["role"] = user["role"]
            st.session_state["keep_signed_in"] = keep_signed_in
            redirect_by_role()
        else:
            st.error("Invalid email or password.")

    if st.button("Forgot password?", use_container_width=True):
        _forgot_password_modal()
