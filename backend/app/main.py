from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from app.middleware.validation import ValidationMiddleware
from app.routes import items as items_router
import logging
import logging.config
import sys

from app.config import settings


# Configure logging centrally and allow log level from settings
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%SZ",
        }
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "default",
            "level": settings.LOG_LEVEL,
        }
    },
    "root": {"handlers": ["stdout"], "level": settings.LOG_LEVEL},
    "loggers": {
        "uvicorn.error": {"level": settings.LOG_LEVEL, "handlers": ["stdout"], "propagate": False},
        "uvicorn.access": {"level": settings.LOG_LEVEL, "handlers": ["stdout"], "propagate": False},
    },
}

logging.config.dictConfig(LOGGING_CONFIG)


def create_app() -> FastAPI:
    app = FastAPI(debug=settings.DEBUG, title=settings.PROJECT_NAME)

    # Validation middleware applied early so requests are sanitized before route handlers
    app.add_middleware(ValidationMiddleware)

    # Allow requests from configured origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Enforce HTTPS when configured (useful for production behind a proxy)
    if settings.FORCE_HTTPS:
        app.add_middleware(HTTPSRedirectMiddleware)

    # Simple security headers middleware
    @app.middleware("http")
    async def set_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        # Disable FLoC / interest-cohort
        response.headers.setdefault("Permissions-Policy", "interest-cohort=()")
        return response

    # include routers
    app.include_router(items_router.router)

    return app


app = create_app()
