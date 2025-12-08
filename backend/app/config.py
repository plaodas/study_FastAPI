from typing import List
import os
import logging


_log = logging.getLogger(__name__)

# Try to use pydantic-settings (modern), fall back to pydantic BaseSettings, and finally
# to a lightweight env-based implementation if neither is available.
try:
    from pydantic_settings import BaseSettings  # type: ignore
    from pydantic import Field, ConfigDict, field_validator  # type: ignore
    _USE_PYDANTIC = True
    _log.debug("Using pydantic-settings BaseSettings for config")
except Exception:
    try:
        from pydantic import BaseSettings, Field, ConfigDict, field_validator  # type: ignore

        _USE_PYDANTIC = True
        _log.debug("Using pydantic BaseSettings for config")
    except Exception:
        BaseSettings = None  # type: ignore
        Field = None  # type: ignore
        _USE_PYDANTIC = False
        _log.debug("pydantic not available; falling back to env-based config")


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes")


def _env_list(name: str, default: List[str]) -> List[str]:
    val = os.getenv(name)
    if not val:
        return default
    return [p.strip() for p in val.split(",") if p.strip()]


if _USE_PYDANTIC:
    class Settings(BaseSettings):
        PROJECT_NAME: str = "study_FastAPI"
        DEBUG: bool = False
        DATABASE_URL: str = "postgresql://user:pass@db:5432/appdb"
        ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
        FORCE_HTTPS: bool = False
        DB_POOL_SIZE: int = 10
        DB_MAX_OVERFLOW: int = 20
        LOG_LEVEL: str = "INFO"
        # Use INTEGRATION_TEST=1 to enable integration tests
        TESTING: bool = False
        # Security / Auth
        SECRET_KEY: str = "change-me"
        JWT_ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

        # Optional runtime
        BACKEND_BASE_URL: str = "http://127.0.0.1:8000"
        PORT: int = 8000

        # DB debug
        DB_ECHO: bool = False

        # Logging / telemetry
        SENTRY_DSN: str = ""

        # Rate limiting / caching
        RATE_LIMIT_ENABLED: bool = False
        RATE_LIMIT_DEFAULT: str = "100/minute"
        REDIS_URL: str = ""

        # Audit / app-specific
        FORBIDDEN_WORDS: List[str] = Field(default_factory=list)
        VALIDATION_RULES: str = ""
        AUDIT_ENABLED: bool = True
        AUDIT_TABLE: str = "item_audit"

        # External services
        BROKER_URL: str = ""

        # Entrypoint helpers
        PYTHONPATH: str = "/app"

        # pydantic v2 style config
        model_config = ConfigDict(
            env_file=os.getenv("ENV_FILE", ".env"),
            env_file_encoding="utf-8",
            extra="allow",
        )

        @field_validator("TESTING", mode="before")
        def _populate_testing_from_integration_env(cls, v):
            # if value provided by other means, keep it
            if v is not None:
                return v
            val = os.getenv("INTEGRATION_TEST")
            if val is None:
                return False
            return str(val).lower() in ("1", "true", "yes")

        @field_validator("FORBIDDEN_WORDS", mode="before")
        def _parse_forbidden_words(cls, v):
            # Accept JSON list or comma-separated string from env
            if v is None:
                return []
            if isinstance(v, str):
                s = v.strip()
                if not s:
                    return []
                if s.startswith("[") or s.startswith("{"):
                    try:
                        import json

                        return json.loads(s)
                    except Exception:
                        # fall back to comma-split if JSON parsing fails
                        return [p.strip() for p in s.split(",") if p.strip()]
                return [p.strip() for p in s.split(",") if p.strip()]
            return v


    try:
        settings = Settings()
    except Exception as e:  # pragma: no cover - defensive fallback when pydantic env parsing fails
        _log.warning("pydantic Settings instantiation failed, falling back to env-based Settings: %s", e)

        # Fallback simple settings implementation that reads from env without complex JSON decoding
        class SimpleSettings:
            PROJECT_NAME: str = os.getenv("PROJECT_NAME", "study_FastAPI")
            DEBUG: bool = _env_bool("DEBUG", False)
            DATABASE_URL: str = os.getenv(
                "DATABASE_URL", "postgresql://user:pass@db:5432/appdb"
            )
            ALLOWED_ORIGINS: List[str] = _env_list("ALLOWED_ORIGINS", ["http://localhost:3000"])
            FORCE_HTTPS: bool = _env_bool("FORCE_HTTPS", False)
            DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
            DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
            LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
            TESTING: bool = _env_bool("INTEGRATION_TEST", False)
            FORBIDDEN_WORDS: List[str] = _env_list("FORBIDDEN_WORDS", [])

        settings = SimpleSettings()
else:
    class Settings:
        PROJECT_NAME: str = os.getenv("PROJECT_NAME", "study_FastAPI")
        DEBUG: bool = _env_bool("DEBUG", False)
        DATABASE_URL: str = os.getenv(
            "DATABASE_URL", "postgresql://user:pass@db:5432/appdb"
        )
        ALLOWED_ORIGINS: List[str] = _env_list("ALLOWED_ORIGINS", ["http://localhost:3000"])
        FORCE_HTTPS: bool = _env_bool("FORCE_HTTPS", False)
        DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
        DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        TESTING: bool = _env_bool("INTEGRATION_TEST", False)


    settings = Settings()
