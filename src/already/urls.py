from __future__ import annotations

from urllib.parse import urlparse

from fastapi import HTTPException

_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata.goog",
}


def require_public_http_url(url: str) -> str:
    if not url or not url.strip():
        raise HTTPException(status_code=422, detail="url is required")
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="url must be http or https")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="url must include a host")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="url must not include credentials")
    host = parsed.hostname.lower().rstrip(".")
    if host in _BLOCKED_HOSTS or host.endswith(".localhost") or host.endswith(".local"):
        raise HTTPException(status_code=400, detail="url is not fetchable")
    if _is_blocked_ip_literal(host):
        raise HTTPException(status_code=400, detail="url is not fetchable")
    return parsed.geturl()


def _is_blocked_ip_literal(host: str) -> bool:
    import ipaddress

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )
