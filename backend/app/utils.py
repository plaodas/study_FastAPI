import re


def sanitize(s: str) -> str:
    # remove HTML tags
    s = re.sub(r"<[^>]*>", "", s)
    # remove control chars except newline/tab/space
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", s)
    # normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_request_metadata(request):
    headers = request.headers
    user_id = headers.get("x-user-id")
    xff = headers.get("x-forwarded-for")
    if xff:
        ip = xff.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else None
    user_agent = headers.get("user-agent")
    request_path = request.url.path if hasattr(request, "url") else None
    method = request.method if hasattr(request, "method") else None
    return {
        "user_id": user_id,
        "ip": ip,
        "user_agent": user_agent,
        "request_path": request_path,
        "method": method,
    }
