from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import json
import re
import os
from typing import List, Tuple


def _load_env_file(path: str) -> dict:
    """Simple .env loader: returns dict of KEY -> VALUE. Ignores comments and blank lines."""
    data = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()
    except Exception:
        pass
    return data


def _get_config_from_env() -> Tuple[List[str], List[Tuple[str, str]]]:
    """Return (forbidden_words, validation_rules).

    validation_rules is list of (path_pattern, method) where path_pattern may end with '*'.
    """
    env = os.environ.copy()
    # Try to read a .env file at project root if present
    root_env = _load_env_file(os.path.join(os.getcwd(), ".env"))
    env.update(root_env)

    forbidden = []
    if "FORBIDDEN_WORDS" in env and env.get("FORBIDDEN_WORDS"):
        forbidden = [
            w.strip() for w in env.get("FORBIDDEN_WORDS").split(",") if w.strip()
        ]

    rules = []
    if "VALIDATION_RULES" in env and env.get("VALIDATION_RULES"):
        raw = env.get("VALIDATION_RULES")
        parts = [p.strip() for p in raw.split(";") if p.strip()]
        for p in parts:
            if ":" in p:
                path, method = p.split(":", 1)
                rules.append((path.strip(), method.strip().upper()))
    return forbidden, rules


def _sanitize(s: str) -> str:
    # remove HTML tags
    s = re.sub(r"<[^>]*>", "", s)
    # remove control chars except newline/tab/space
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", s)
    # normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware that centralizes input validation/sanitization for selected endpoints.

    Currently handles:
    - POST /items : validates JSON body contains `name` (1-100 chars), sanitizes it,
      checks forbidden words, and replaces the request body with the sanitized JSON
      so downstream handlers receive the cleaned payload.
    """

    async def dispatch(self, request: Request, call_next):
        forbidden, rules = _get_config_from_env()

        # If no rules are configured, default to POST /items for backward compatibility
        if not rules:
            rules = [("/items", "POST")]

        # check if current request matches any rule
        matched = False
        path = request.url.path
        method = request.method.upper()
        for pattern, m in rules:
            if m != method:
                continue
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if path.startswith(prefix):
                    matched = True
                    break
            else:
                if path == pattern:
                    matched = True
                    break

        if matched:
            body_bytes = await request.body()
            try:
                data = json.loads(body_bytes) if body_bytes else {}
            except Exception:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid JSON body"},
                )

            name = data.get("name")
            if not isinstance(name, str):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "`name` is required and must be a string"},
                )
            if not (1 <= len(name) <= 100):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "`name` must be 1-100 characters long"},
                )

            name_clean = _sanitize(name)

            low = name_clean.lower()
            for fw in forbidden:
                if fw and fw.lower() in low:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": "Name contains forbidden content"},
                    )

            validated = {"name": name_clean}

            # Replace the request body so downstream dependencies (e.g., pydantic) parse the sanitized data
            new_body = json.dumps(validated).encode()

            async def receive() -> dict:
                return {"type": "http.request", "body": new_body}

            # Monkey-patch the receive function used by the request to supply the cleaned body
            request._receive = receive
            # Also stash validated data for handlers that prefer to read it directly
            request.state.validated_json = validated

        response = await call_next(request)
        return response
