import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_st():
    """Provide a fake streamlit module so session.py imports cleanly."""
    st = MagicMock()
    st.session_state = {}
    with patch.dict("sys.modules", {"streamlit": st}):
        yield st


def test_current_user_id(mock_st):
    mock_st.session_state = {"user_id": 42}
    from importlib import reload
    import utils.session as s
    reload(s)
    assert s.current_user_id() == 42


def test_current_username(mock_st):
    mock_st.session_state = {"username": "alice"}
    from importlib import reload
    import utils.session as s
    reload(s)
    assert s.current_username() == "alice"


def test_current_user_role_default(mock_st):
    mock_st.session_state = MagicMock()
    mock_st.session_state.get = lambda k, d=None: d
    from importlib import reload
    import utils.session as s
    reload(s)
    assert s.current_user_role() == "user"


def test_current_user_role_admin(mock_st):
    mock_st.session_state = MagicMock()
    mock_st.session_state.get = lambda k, d=None: "admin" if k == "role" else d
    from importlib import reload
    import utils.session as s
    reload(s)
    assert s.current_user_role() == "admin"


def test_redirect_by_role_calls_rerun(mock_st):
    from importlib import reload
    import utils.session as s
    reload(s)
    s.redirect_by_role()
    mock_st.rerun.assert_called_once()
