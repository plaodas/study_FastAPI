"""Unit tests for `app.utils.sanitize`.

Checks HTML tag removal, control character stripping, whitespace normalization and
empty-string behavior. These are small, deterministic unit tests that do not
require DB or network access.
"""

import pytest

from app.utils import sanitize


# Removes HTML tags
def test_sanitize_removes_html_tags():
    assert sanitize("<b>Hello</b>") == "Hello"


# Removes control chars and normalizes whitespace (tabs/newlines -> single spaces)
def test_sanitize_removes_control_chars_and_normalizes_whitespace():
    s = "a\x01b\t\tc\n\n  d"
    assert sanitize(s) == "ab c d"


# Collapses multiple spaces and trims ends
def test_sanitize_trims_and_collapses_spaces():
    assert sanitize("  foo   bar  ") == "foo bar"


# Empty string remains empty
def test_sanitize_empty_string():
    assert sanitize("") == ""
