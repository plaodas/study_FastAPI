from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.validation import ValidationMiddleware
from app.routes import items as items_router
import logging
import logging.config
import sys

# Configure logging centrally so INFO+ messages from the app and uvicorn
# are always emitted to stdout/stderr (which the entrypoint redirects to
# `/app/logs/uvicorn.log`). Use a simple dictConfig so handlers/formatters
# are consistent across environments.
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
            "level": "INFO",
        }
    },
    "root": {"handlers": ["stdout"], "level": "INFO"},
    "loggers": {
        "uvicorn.error": {"level": "INFO", "handlers": ["stdout"], "propagate": False},
        "uvicorn.access": {"level": "INFO", "handlers": ["stdout"], "propagate": False},
    },
}

logging.config.dictConfig(LOGGING_CONFIG)


def create_app() -> FastAPI:
    app = FastAPI()

    # Validation middleware applied early so requests are sanitized before route handlers
    app.add_middleware(ValidationMiddleware)

    # Allow requests from the frontend dev server during development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # include routers
    app.include_router(items_router.router)

    return app


app = create_app()
