import pytest
from unittest.mock import MagicMock, patch, call


@pytest.fixture(autouse=True)
def mock_st():
    st = MagicMock()
    with patch.dict("sys.modules", {"streamlit": st}):
        yield st


def _render(msg, is_own=False):
    from importlib import reload
    import components.message_list as m
    reload(m)
    m.render_message(msg, is_own=is_own)


def _make_msg(**kwargs):
    base = {"author": "alice", "created_at": "2026-01-01 10:00", "edited_at": None,
            "reply_to_id": None, "content": "hello"}
    base.update(kwargs)
    return base


def test_render_message_calls_markdown(mock_st):
    _render(_make_msg())
    mock_st.markdown.assert_called_once()


def test_render_message_shows_author(mock_st):
    _render(_make_msg(author="bob"))
    call_text = mock_st.markdown.call_args[0][0]
    assert "bob" in call_text


def test_render_message_edited_indicator(mock_st):
    _render(_make_msg(edited_at="2026-01-01 11:00"))
    call_text = mock_st.markdown.call_args[0][0]
    assert "edited" in call_text


def test_render_message_no_edited_indicator_when_none(mock_st):
    _render(_make_msg(edited_at=None))
    call_text = mock_st.markdown.call_args[0][0]
    assert "edited" not in call_text


def test_render_message_reply_shows_caption(mock_st):
    _render(_make_msg(reply_to_id=5))
    mock_st.caption.assert_called_once()
    assert "5" in mock_st.caption.call_args[0][0]


def test_render_message_no_reply_skips_caption(mock_st):
    _render(_make_msg(reply_to_id=None))
    mock_st.caption.assert_not_called()


def test_render_message_writes_content(mock_st):
    _render(_make_msg(content="test content"))
    mock_st.write.assert_called_once_with("test content")
