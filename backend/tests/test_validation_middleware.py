"""Integration tests for ValidationMiddleware.

These tests use the `prepare_db` fixture to provide a shared SQLite engine for
`TestClient`. Tests may mutate `app.config.settings` at runtime; the middleware
proxies settings so runtime changes are observed.
"""

import os
from fastapi.testclient import TestClient


# Middleware should block requests containing forbidden words
def test_middleware_blocks_forbidden(monkeypatch, prepare_db):
    # ensure DB prepared by fixture and app is imported after config mutation
    import app.config as conf
    conf.settings.FORBIDDEN_WORDS = ["forbidden"]
    conf.settings.VALIDATION_RULES = [("/items", "POST")]

    # create app after settings set so middleware sees the configured rules
    from app.main import app

    client = TestClient(app)
    resp = client.post("/items", json={"name": "this contains forbidden word"})
    assert resp.status_code == 400


# Middleware should match configured POST /items rule and sanitize the body
def test_middleware_matches_prefix_rule(prepare_db):
    import app.config as conf
    conf.settings.VALIDATION_RULES = [("/items", "POST")]

    from app.main import app
    client = TestClient(app)
    data = {"name": "  <b>hello</b>\nworld"}
    resp = client.post("/items", json=data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "hello world"


# Ensure middleware sanitizes once and route does not re-sanitize
def test_middleware_and_route_do_not_double_sanitize(monkeypatch, prepare_db):
    from app.main import app

    calls = {"count": 0}

    def fake_sanitize(s: str) -> str:
        calls["count"] += 1
        return s.replace("<b>", "").replace("</b>", "")

    # patch both modules' sanitized references
    monkeypatch.setattr("app.middleware.validation.sanitize", fake_sanitize)
    monkeypatch.setattr("app.routes.items.sanitize", fake_sanitize)

    client = TestClient(app)
    resp = client.post("/items", json={"name": "<b>Hi</b>"})
    assert resp.status_code == 201
    # middleware should call sanitize once; route should skip second call
    assert calls["count"] == 1
