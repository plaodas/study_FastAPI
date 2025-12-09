import pytest

from app.utils import sanitize


def test_sanitize_removes_html_tags():
    assert sanitize("<b>Hello</b>") == "Hello"


def test_sanitize_removes_control_chars_and_normalizes_whitespace():
    # contains a control char (\x01), tabs and newlines
    s = "a\x01b\t\tc\n\n  d"
    # expected: control char removed, tabs/newlines collapsed to single spaces
    assert sanitize(s) == "ab c d"


def test_sanitize_trims_and_collapses_spaces():
    assert sanitize("  foo   bar  ") == "foo bar"


def test_sanitize_empty_string():
    assert sanitize("") == ""
