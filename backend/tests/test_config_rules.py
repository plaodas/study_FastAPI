"""Tests for the validation-rules parser in `app.config`.

The parser accepts strings (semicolon-separated) or lists/tuples and
normalizes them to a list of (path, METHOD) tuples.
"""

from app.config import _parse_validation_rules


# String input with multiple rules
def test_parse_validation_rules_from_string():
    raw = "/items:POST;/items/*:PUT"
    parsed = _parse_validation_rules(raw)
    assert ("/items", "POST") in parsed
    assert ("/items/*", "PUT") in parsed


# List input with mixed case method names
def test_parse_validation_rules_from_list():
    raw = ["/a:GET", "/b:post"]
    parsed = _parse_validation_rules(raw)
    assert parsed == [("/a", "GET"), ("/b", "POST")]


# Empty or None returns empty list
def test_parse_validation_rules_empty():
    assert _parse_validation_rules("") == []
    assert _parse_validation_rules(None) == []
