import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_st():
    st = MagicMock()
    st.button.return_value = False
    st.columns.side_effect = lambda spec: [MagicMock() for _ in spec]
    with patch.dict("sys.modules", {"streamlit": st}):
        yield st


def _nav():
    from importlib import reload
    import components.navigation as nav
    reload(nav)
    return nav


# ── nav_login ─────────────────────────────────────────────────────────────────

def test_nav_login_returns_none_when_no_button_clicked(mock_st):
    nav = _nav()
    result = nav.nav_login()
    assert result is None


def test_nav_login_returns_signin_when_signin_clicked(mock_st):
    mock_st.button.side_effect = lambda label, **kw: label == "Sign in"
    nav = _nav()
    result = nav.nav_login()
    assert result == "signin"


def test_nav_login_returns_register_when_register_clicked(mock_st):
    mock_st.button.side_effect = lambda label, **kw: label == "Register"
    nav = _nav()
    result = nav.nav_login()
    assert result == "register"


def test_nav_login_calls_divider(mock_st):
    nav = _nav()
    nav.nav_login()
    mock_st.divider.assert_called()


# ── nav_user ──────────────────────────────────────────────────────────────────

def test_nav_user_returns_none_when_no_button_clicked(mock_st):
    nav = _nav()
    result = nav.nav_user()
    assert result is None


def test_nav_user_returns_public_rooms_action(mock_st):
    mock_st.button.side_effect = lambda label, **kw: label == "Public Rooms"
    nav = _nav()
    result = nav.nav_user()
    assert result == "public_rooms"


def test_nav_user_returns_private_rooms_action(mock_st):
    mock_st.button.side_effect = lambda label, **kw: label == "Private Rooms"
    nav = _nav()
    result = nav.nav_user()
    assert result == "private_rooms"


def test_nav_user_returns_contacts_action(mock_st):
    mock_st.button.side_effect = lambda label, **kw: label == "Contacts"
    nav = _nav()
    result = nav.nav_user()
    assert result == "contacts"


def test_nav_user_returns_sessions_action(mock_st):
    mock_st.button.side_effect = lambda label, **kw: label == "Sessions"
    nav = _nav()
    result = nav.nav_user()
    assert result == "sessions"


def test_nav_user_returns_profile_action(mock_st):
    mock_st.button.side_effect = lambda label, **kw: label == "Profile"
    nav = _nav()
    result = nav.nav_user()
    assert result == "profile"


def test_nav_user_returns_signout_action(mock_st):
    mock_st.button.side_effect = lambda label, **kw: label == "Sign out"
    nav = _nav()
    result = nav.nav_user()
    assert result == "signout"


# ── nav_admin ─────────────────────────────────────────────────────────────────

def test_nav_admin_no_rooms_shows_caption(mock_st):
    nav = _nav()
    result = nav.nav_admin(None)
    mock_st.caption.assert_called_with("No rooms available")
    assert result is None


def test_nav_admin_empty_list_shows_caption(mock_st):
    nav = _nav()
    nav.nav_admin([])
    mock_st.caption.assert_called_with("No rooms available")


def test_nav_admin_with_rooms_calls_selectbox(mock_st):
    rooms = [{"name": "general"}, {"name": "random"}]
    nav = _nav()
    nav.nav_admin(rooms)
    mock_st.selectbox.assert_called_once_with(
        "Manage room", options=["general", "random"], key="admin_selected_room"
    )


def test_nav_admin_returns_none_when_no_signout(mock_st):
    nav = _nav()
    result = nav.nav_admin([])
    assert result is None


def test_nav_admin_returns_signout_when_button_clicked(mock_st):
    mock_st.button.return_value = True
    nav = _nav()
    result = nav.nav_admin([])
    assert result == "signout"


def test_nav_admin_calls_divider(mock_st):
    nav = _nav()
    nav.nav_admin(None)
    mock_st.divider.assert_called()
