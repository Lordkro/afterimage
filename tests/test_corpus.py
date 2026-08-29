import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from afterimage.app import create_app
from afterimage.models import Snapshot
from afterimage.settings import Settings
from tests.fakes import FakeClock, FakeFetcher, FakePage, MemorySnapshotStore


def _page(title: str, body: str, url: str) -> tuple[str, FakePage]:
    html = (
        f"<!DOCTYPE html><html><head><title>{title}</title></head>"
        f"<body><p>{body}</p></body></html>"
    ).encode()
    return url, FakePage(body=html)


def _client(
    pages: dict[str, FakePage],
    *,
    settings: Settings,
    clock: FakeClock | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            fetcher=FakeFetcher(pages),
            store=MemorySnapshotStore(),
            clock=clock or FakeClock(),
            settings=settings,
        )
    )


def test_oldest_snapshots_are_evicted_when_the_corpus_is_full() -> None:
    pages = dict(
        [
            _page("Alpha", "alpha unique token", "https://example.com/a"),
            _page("Beta", "beta unique token", "https://example.com/b"),
            _page("Gamma", "gamma unique token", "https://example.com/c"),
        ]
    )
    clock = FakeClock()
    client = _client(
        pages,
        settings=Settings(max_snapshots=2, snapshot_ttl_s=10_000_000),
        clock=clock,
    )
    for path in ("a", "b", "c"):
        assert (
            client.get("/v1/page", params={"url": f"https://example.com/{path}"}).status_code
            == 200
        )
        clock.advance(1)

    indexed = client.get("/v1/search", params={"q": "token"}).json()
    urls = {hit["url"] for hit in indexed["hits"]}
    assert indexed["indexed"] == 2
    assert "https://example.com/a" not in urls
    assert "https://example.com/b" in urls
    assert "https://example.com/c" in urls


def test_expired_snapshots_are_dropped_from_the_corpus() -> None:
    url, page = _page("Pricing", "Pro is $9 per month", "https://example.com/pricing")
    clock = FakeClock()
    client = _client(
        {url: page},
        settings=Settings(max_snapshots=100, snapshot_ttl_s=60),
        clock=clock,
    )
    assert client.get("/v1/page", params={"url": url}).status_code == 200
    clock.advance(61)

    body = client.get("/v1/search", params={"q": "pricing"}).json()
    assert body["indexed"] == 0
    assert body["hits"] == []


def test_stored_text_is_capped() -> None:
    blob = ("lorem ipsum " * 500).strip()
    url, page = _page("Huge", blob, "https://example.com/huge")
    client = _client(
        {url: page},
        settings=Settings(max_text_chars=80, max_snapshots=10, snapshot_ttl_s=10_000_000),
    )

    response = client.get("/v1/page", params={"url": url})
    text = response.json()["text"]
    assert len(text) <= 80
    assert text.startswith("lorem ipsum")


def test_status_pages_are_fetched_live_and_not_stored() -> None:
    url = "https://status.openai.com/"
    html = (
        b"<!DOCTYPE html><html><head><title>OpenAI Status</title></head>"
        b"<body><main><p>All systems operational</p></main></body></html>"
    )
    client = _client(
        {url: FakePage(body=html)},
        settings=Settings(max_snapshots=100, snapshot_ttl_s=10_000_000),
    )
    body = client.get("/v1/page", params={"url": url}).json()
    assert body["stored"] is False
    assert body["stored_reason"] == "volatile"
    assert "All systems operational" in body["text"]
    search = client.get("/v1/search", params={"q": "operational"}).json()
    assert search["indexed"] == 0
    assert search["hits"] == []


def test_already_stored_status_pages_are_dropped_from_search() -> None:
    store = MemorySnapshotStore()
    now = datetime(2026, 8, 27, 18, 41, 2, tzinfo=UTC)
    asyncio.run(
        store.put(
            Snapshot(
                url="https://status.anthropic.com/",
                final_url="https://status.anthropic.com/",
                status=200,
                title="Anthropic Status",
                text="All systems operational",
                content_hash="sha256:" + "a" * 64,
                fetched_at=now,
                content_type="text/html",
            )
        )
    )
    client = TestClient(
        create_app(
            fetcher=FakeFetcher({}),
            store=store,
            clock=FakeClock(),
            settings=Settings(max_snapshots=100, snapshot_ttl_s=10_000_000),
        )
    )
    body = client.get("/v1/search", params={"q": "operational"}).json()
    assert body["indexed"] == 0
    assert body["hits"] == []


def test_error_pages_are_not_kept_in_the_corpus() -> None:
    url = "https://example.com/gone"
    client = _client(
        {
            url: FakePage(
                body=b"<html><head><title>Nope</title></head><body>Missing</body></html>",
                status=404,
            )
        },
        settings=Settings(max_snapshots=10, snapshot_ttl_s=10_000_000),
    )
    page = client.get("/v1/page", params={"url": url})
    assert page.status_code == 200
    assert page.json()["status"] == 404

    search = client.get("/v1/search", params={"q": "Missing"}).json()
    assert search["indexed"] == 0
    assert search["hits"] == []
