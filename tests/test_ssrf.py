import pytest
from fastapi.testclient import TestClient

from already.app import create_app
from tests.fakes import FakeFetcher, MemorySnapshotStore

BLOCKED = [
    "http://127.0.0.1/",
    "http://localhost/secret",
    "http://10.0.0.8/admin",
    "http://192.168.1.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]/",
    "file:///etc/passwd",
    "ftp://example.com/file",
]


@pytest.mark.parametrize("url", BLOCKED)
def test_private_and_non_http_urls_are_rejected(url: str) -> None:
    fetcher = FakeFetcher({})
    client = TestClient(
        create_app(fetcher=fetcher, store=MemorySnapshotStore())
    )

    response = client.get("/v1/page", params={"url": url})

    assert response.status_code in {400, 422}
    assert fetcher.calls == []
