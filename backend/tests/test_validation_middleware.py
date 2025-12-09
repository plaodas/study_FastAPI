import os
from fastapi.testclient import TestClient


def test_middleware_blocks_forbidden(monkeypatch, prepare_db):
    # ensure DB prepared by fixture
    from app.main import app
    import app.config as conf

    # set forbidden words on settings (both global config and middleware-local reference)
    conf.settings.FORBIDDEN_WORDS = ["forbidden"]
    # ensure middleware applies to POST /items in this test
    conf.settings.VALIDATION_RULES = [("/items", "POST")]
    # sometimes the middleware module holds its own reference to settings;
    # set the value there too to be certain
    try:
        import app.middleware.validation as vmod

        vmod.settings.FORBIDDEN_WORDS = ["forbidden"]
        vmod.settings.VALIDATION_RULES = [("/items", "POST")]
    except Exception:
        pass

    client = TestClient(app)
    resp = client.post("/items", json={"name": "this contains forbidden word"})
    assert resp.status_code == 400


def test_middleware_matches_prefix_rule(prepare_db):
    from app.main import app
    import app.config as conf

    # configure validation rule to match the /items POST
    conf.settings.VALIDATION_RULES = [("/items", "POST")]

    client = TestClient(app)
    data = {"name": "  <b>hello</b>\nworld"}
    resp = client.post("/items", json=data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "hello world"


def test_middleware_and_route_do_not_double_sanitize(monkeypatch, prepare_db):
    from app.main import app

    calls = {"count": 0}

    def fake_sanitize(s: str) -> str:
        calls["count"] += 1
        # simple pass-through that removes HTML tags for the test
        return s.replace("<b>", "").replace("</b>", "")

    # patch both modules' sanitized references
    monkeypatch.setattr("app.middleware.validation.sanitize", fake_sanitize)
    monkeypatch.setattr("app.routes.items.sanitize", fake_sanitize)

    client = TestClient(app)
    resp = client.post("/items", json={"name": "<b>Hi</b>"})
    assert resp.status_code == 201
    # middleware should call sanitize once; route should skip second call
    assert calls["count"] == 1
