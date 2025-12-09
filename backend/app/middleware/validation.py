from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import json
from typing import List, Tuple

from app.utils import sanitize
import app.config as conf


class _SettingsProxy:
    """Proxy object that delegates attribute access to `app.config.settings`.

    This lets other modules assign to `vmod.settings.<attr>` in tests or runtime
    and have the changes reflected in the central `app.config.settings` object.
    """
    def __getattr__(self, name):
        s = getattr(conf, "settings", None)
        if s is None:
            raise AttributeError(name)
        return getattr(s, name)

    def __setattr__(self, name, value):
        s = getattr(conf, "settings", None)
        if s is None:
            # fallback: set attribute on this proxy
            return object.__setattr__(self, name, value)
        return setattr(s, name, value)


settings = _SettingsProxy()


def _get_config_from_settings() -> Tuple[List[str], List[Tuple[str, str]]]:
    """Return (forbidden_words, validation_rules) using `app.config.settings`.

    `validation_rules` is a list of (path_pattern, method) where path_pattern may end with '*'.
    """
    forbidden = []
    try:
        fw = getattr(settings, "FORBIDDEN_WORDS", None)
        if fw:
            # settings.FORBIDDEN_WORDS may already be a list
            if isinstance(fw, (list, tuple)):
                forbidden = [str(x).strip() for x in fw if str(x).strip()]
            else:
                forbidden = [p.strip() for p in str(fw).split(",") if p.strip()]
    except Exception:
        forbidden = []

    rules = []
    try:
        raw = getattr(settings, "VALIDATION_RULES", None)
        if raw:
            # Accept several input shapes: string, list of strings, or list of tuples
            if isinstance(raw, str):
                parts = [p.strip() for p in raw.split(";") if p.strip()]
                for p in parts:
                    if ":" in p:
                        path, method = p.split(":", 1)
                        rules.append((path.strip(), method.strip().upper()))
            elif isinstance(raw, (list, tuple)):
                for entry in raw:
                    # tuple/list like (path, method)
                    if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                        rules.append((str(entry[0]).strip(), str(entry[1]).strip().upper()))
                    else:
                        s = str(entry).strip()
                        if ":" in s:
                            path, method = s.split(":", 1)
                            rules.append((path.strip(), method.strip().upper()))
            else:
                # unknown format -> ignore
                pass
    except Exception:
        rules = []

    return forbidden, rules


class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware that centralizes input validation/sanitization for selected endpoints.

    Currently handles:
    - POST /items : validates JSON body contains `name` (1-100 chars), sanitizes it,
      checks forbidden words, and replaces the request body with the sanitized JSON
      so downstream handlers receive the cleaned payload.
    """

    async def dispatch(self, request: Request, call_next):
        forbidden, rules = _get_config_from_settings()

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

            name_clean = sanitize(name)

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
