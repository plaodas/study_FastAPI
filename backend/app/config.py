from typing import List
import os


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


class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "study_FastAPI")
    DEBUG: bool = _env_bool("DEBUG", False)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@db:5432/appdb")
    ALLOWED_ORIGINS: List[str] = _env_list("ALLOWED_ORIGINS", ["http://localhost:3000"])
    FORCE_HTTPS: bool = _env_bool("FORCE_HTTPS", False)
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    TESTING: bool = _env_bool("INTEGRATION_TEST", False)


settings = Settings()
