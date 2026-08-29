from fastapi.testclient import TestClient

from afterimage.app import create_app
from tests.fakes import FakeClock, FakeFetcher, FakePage, MemorySnapshotStore

PRICING_HTML = b"""<!DOCTYPE html>
<html>
  <head><title>Pricing</title></head>
  <body>
    <nav>Home</nav>
    <main>
      <h1>Plans</h1>
      <p>Pro is $9 per month.</p>
    </main>
    <script>alert('ignore')</script>
  </body>
</html>
"""


def _client(fetcher: FakeFetcher | None = None, clock: FakeClock | None = None) -> TestClient:
    return TestClient(
        create_app(
            fetcher=fetcher
            or FakeFetcher(
                {"https://example.com/pricing": FakePage(body=PRICING_HTML)}
            ),
            store=MemorySnapshotStore(),
            clock=clock or FakeClock(),
        )
    )


def test_page_fetch_returns_readable_snapshot_on_miss() -> None:
    client = _client()

    response = client.get("/v1/page", params={"url": "https://example.com/pricing"})

    assert response.status_code == 200
    body = response.json()
    assert body["url"] == "https://example.com/pricing"
    assert body["final_url"] == "https://example.com/pricing"
    assert body["status"] == 200
    assert body["title"] == "Pricing"
    assert "Pro is $9 per month." in body["text"]
    assert "Home" not in body["text"]
    assert "<html>" not in body["text"]
    assert "alert(" not in body["text"]
    assert body["hash"].startswith("sha256:")
    assert len(body["hash"]) == len("sha256:") + 64
    assert body["fetched_at"] == "2026-08-27T18:41:02Z"
    assert body["age_s"] == 0
    assert body["cache"] == "miss"
    assert body["price_usdc"] == "0.01"
    assert body["truncated"] is False


def test_fresh_snapshot_is_reused_instead_of_refetching() -> None:
    clock = FakeClock()
    fetcher = FakeFetcher({"https://example.com/pricing": FakePage(body=PRICING_HTML)})
    client = TestClient(
        create_app(fetcher=fetcher, store=MemorySnapshotStore(), clock=clock)
    )

    first = client.get("/v1/page", params={"url": "https://example.com/pricing"})
    clock.advance(60)
    second = client.get(
        "/v1/page", params={"url": "https://example.com/pricing", "max_age_s": 900}
    )

    assert first.status_code == 200
    assert second.status_code == 200
    body = second.json()
    assert body["cache"] == "hit"
    assert body["hash"] == first.json()["hash"]
    assert body["fetched_at"] == first.json()["fetched_at"]
    assert body["age_s"] == 60
    assert body["price_usdc"] == "0.002"
    assert fetcher.calls == ["https://example.com/pricing"]


def test_stale_snapshot_is_fetched_again() -> None:
    clock = FakeClock()
    fetcher = FakeFetcher({"https://example.com/pricing": FakePage(body=PRICING_HTML)})
    client = TestClient(
        create_app(fetcher=fetcher, store=MemorySnapshotStore(), clock=clock)
    )

    first = client.get("/v1/page", params={"url": "https://example.com/pricing"})
    clock.advance(901)
    second = client.get(
        "/v1/page", params={"url": "https://example.com/pricing", "max_age_s": 900}
    )

    assert first.json()["cache"] == "miss"
    body = second.json()
    assert body["cache"] == "miss"
    assert body["age_s"] == 0
    assert body["fetched_at"] == "2026-08-27T18:56:03Z"
    assert body["price_usdc"] == "0.01"
    assert fetcher.calls == [
        "https://example.com/pricing",
        "https://example.com/pricing",
    ]


def test_origin_errors_are_still_snapshots() -> None:
    fetcher = FakeFetcher(
        {
            "https://example.com/gone": FakePage(
                body=b"<html><head><title>Nope</title></head><body>Missing</body></html>",
                status=404,
            )
        }
    )
    client = TestClient(
        create_app(fetcher=fetcher, store=MemorySnapshotStore(), clock=FakeClock())
    )

    response = client.get("/v1/page", params={"url": "https://example.com/gone"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == 404
    assert body["title"] == "Nope"
    assert "Missing" in body["text"]
    assert body["cache"] == "miss"
