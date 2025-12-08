from typing import List
import os
import logging


_log = logging.getLogger(__name__)

# Try to use pydantic-settings (modern), fall back to pydantic BaseSettings, and finally
# to a lightweight env-based implementation if neither is available.
try:
    from pydantic_settings import BaseSettings  # type: ignore
    from pydantic import Field  # type: ignore
    _USE_PYDANTIC = True
    _log.debug("Using pydantic-settings BaseSettings for config")
except Exception:
    try:
        from pydantic import BaseSettings, Field  # type: ignore

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
        TESTING: bool = Field(False, env="INTEGRATION_TEST")

        class Config:
            env_file = os.getenv("ENV_FILE", ".env")
            env_file_encoding = "utf-8"


    settings = Settings()
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
