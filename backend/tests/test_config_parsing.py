import importlib


def test_settings_parses_env_vars(monkeypatch):
    """Verify settings are read from environment and complex types handled.

    This test reloads `app.config` to exercise different Settings implementations
    (pydantic-based or simple env-based fallback).
    """
    # set a variety of env vars and reload the config module to pick them up
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DB_POOL_SIZE", "33")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "5")
    # For pydantic-backed settings, complex types are expected as JSON strings
    monkeypatch.setenv("FORBIDDEN_WORDS", '["spam","bad"]')
    # ensure dotenv file is not loaded in test (avoid existing .env interfering)
    monkeypatch.setenv("ENV_FILE", "/tmp/pytest-no-env.env")
    monkeypatch.setenv("VALIDATION_RULES", "/items:POST")
    monkeypatch.setenv("INTEGRATION_TEST", "1")
    # also set TESTING env var to cover different settings implementations
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setenv("SECRET_KEY", "s3cr3t")

    import app.config as conf
    importlib.reload(conf)

    s = conf.settings

    # common fields
    assert getattr(s, "LOG_LEVEL", "").upper() == "DEBUG"
    assert int(getattr(s, "DB_POOL_SIZE", 0)) == 33
    assert int(getattr(s, "DB_MAX_OVERFLOW", 0)) == 5

    # list parsing
    fw = getattr(s, "FORBIDDEN_WORDS", None)
    # allow both list or comma-joined string depending on impl
    if isinstance(fw, str):
        assert "spam" in fw
    else:
        assert "spam" in fw

    vr = getattr(s, "VALIDATION_RULES", "")
    # VALIDATION_RULES may be normalized to a parsed list of tuples by config
    if isinstance(vr, str):
        assert vr == "/items:POST"
    else:
        assert vr == [("/items", "POST")]

    # testing flag
    assert bool(getattr(s, "TESTING", False)) is True

    # secret
    assert getattr(s, "SECRET_KEY", "") == "s3cr3t"
