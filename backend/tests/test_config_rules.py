from app.config import _parse_validation_rules


def test_parse_validation_rules_from_string():
    raw = "/items:POST;/items/*:PUT"
    parsed = _parse_validation_rules(raw)
    assert ("/items", "POST") in parsed
    assert ("/items/*", "PUT") in parsed


def test_parse_validation_rules_from_list():
    raw = ["/a:GET", "/b:post"]
    parsed = _parse_validation_rules(raw)
    assert parsed == [("/a", "GET"), ("/b", "POST")]


def test_parse_validation_rules_empty():
    assert _parse_validation_rules("") == []
    assert _parse_validation_rules(None) == []
