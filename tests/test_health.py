from fastapi.testclient import TestClient

from afterimage.app import create_app
from tests.fakes import FakeClock, FakeFetcher, FakePage, MemorySnapshotStore
from tests.test_page import PRICING_HTML


def test_health_reports_ready() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "afterimage"
    assert body["indexed"] == 0


def test_stats_is_free_and_reports_live_corpus_size() -> None:
    store = MemorySnapshotStore()
    client = TestClient(
        create_app(
            fetcher=FakeFetcher(
                {"https://example.com/pricing": FakePage(body=PRICING_HTML)}
            ),
            store=store,
            clock=FakeClock(),
        )
    )
    assert client.get("/v1/page", params={"url": "https://example.com/pricing"}).status_code == 200

    stats = client.get("/v1/stats")
    health = client.get("/health")

    assert stats.status_code == 200
    body = stats.json()
    assert body["indexed"] == 1
    assert body["max_snapshots"] == 5000
    assert body["max_text_chars"] == 32_000
    assert body["snapshot_ttl_s"] == 7 * 24 * 60 * 60
    assert health.json()["indexed"] == 1
