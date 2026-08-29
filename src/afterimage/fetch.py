from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import HTTPException

from afterimage.models import FetchResult
from afterimage.urls import require_public_http_url

MAX_BYTES = 5_000_000
MAX_REDIRECTS = 5
TIMEOUT_S = 15.0
USER_AGENT = "AfterImage/0.1 (+https://github.com/Lordkro/afterimage; agent-snapshot)"

Resolver = Callable[..., list]


def resolve_public_host(host: str, resolver: Resolver = socket.getaddrinfo) -> None:
    try:
        answers = resolver(host, None)
    except OSError as exc:
        raise HTTPException(status_code=400, detail="url host could not be resolved") from exc
    if not answers:
        raise HTTPException(status_code=400, detail="url host could not be resolved")
    for answer in answers:
        sockaddr = answer[4]
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise HTTPException(status_code=400, detail="url is not fetchable")


class HttpxFetcher:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        resolver: Resolver = socket.getaddrinfo,
    ) -> None:
        self._client = client
        self._resolver = resolver
        self._owns_client = client is None

    async def fetch(self, url: str) -> FetchResult:
        url = require_public_http_url(url)
        client = self._client or httpx.AsyncClient(
            follow_redirects=False,
            timeout=TIMEOUT_S,
            headers={"User-Agent": USER_AGENT},
        )
        try:
            current = url
            for _ in range(MAX_REDIRECTS + 1):
                require_public_http_url(current)
                host = urlparse(current).hostname
                if not host:
                    raise HTTPException(status_code=400, detail="url is not fetchable")
                resolve_public_host(host, self._resolver)
                response = await client.get(current)
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise HTTPException(status_code=502, detail="redirect without location")
                    current = urljoin(current, location)
                    continue
                body = response.content[: MAX_BYTES + 1]
                if len(body) > MAX_BYTES:
                    raise HTTPException(status_code=413, detail="response too large")
                return FetchResult(
                    url=url,
                    final_url=str(response.url),
                    status=response.status_code,
                    body=body,
                    content_type=response.headers.get("content-type", "application/octet-stream"),
                    headers={k.lower(): v for k, v in response.headers.items()},
                )
            raise HTTPException(status_code=400, detail="too many redirects")
        finally:
            if self._owns_client:
                await client.aclose()
