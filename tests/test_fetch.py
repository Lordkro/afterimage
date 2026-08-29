import pytest
from fastapi import HTTPException

from afterimage.fetch import REQUEST_HEADERS, HttpxFetcher


def _loopback_resolver(host: str, port: object, *args: object, **kwargs: object) -> list:
    return [(2, 1, 6, "", ("127.0.0.1", 0))]


@pytest.mark.asyncio
async def test_fetcher_refuses_hosts_that_resolve_to_loopback() -> None:
    fetcher = HttpxFetcher(resolver=_loopback_resolver)

    with pytest.raises(HTTPException) as err:
        await fetcher.fetch("https://evil.example/hidden")

    assert err.value.status_code == 400
    assert err.value.detail == "url is not fetchable"


def test_fetcher_uses_a_fixed_anonymous_header_set() -> None:
    assert REQUEST_HEADERS["Accept-Language"] == "en-US,en;q=0.9"
    assert "Cookie" not in REQUEST_HEADERS
    assert "Authorization" not in REQUEST_HEADERS
    assert REQUEST_HEADERS["User-Agent"].startswith("AfterImage/")
