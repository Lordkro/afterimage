from fastapi.testclient import TestClient

from afterimage.app import create_app
from tests.fakes import FakeClock, FakeFetcher, FakePage, MemorySnapshotStore
from tests.test_page import PRICING_HTML

DOCS_HTML = b"""<!DOCTYPE html>
<html>
  <head><title>FastAPI Background Tasks</title></head>
  <body>
    <main>
      <p>Use BackgroundTasks to run work after the response is sent.</p>
    </main>
  </body>
</html>
"""


def _client(
    pages: dict[str, FakePage] | None = None,
    *,
    store: MemorySnapshotStore | None = None,
    clock: FakeClock | None = None,
    fetcher: FakeFetcher | None = None,
) -> tuple[TestClient, FakeFetcher]:
    fetcher = fetcher or FakeFetcher(
        pages
        or {"https://example.com/pricing": FakePage(body=PRICING_HTML)}
    )
    client = TestClient(
        create_app(
            fetcher=fetcher,
            store=store or MemorySnapshotStore(),
            clock=clock or FakeClock(),
        )
    )
    return client, fetcher


def test_search_finds_a_previously_fetched_page_without_refetching() -> None:
    client, fetcher = _client()
    seeded = client.get("/v1/page", params={"url": "https://example.com/pricing"})
    assert seeded.status_code == 200
    fetcher.calls.clear()

    response = client.get("/v1/search", params={"q": "Pro is $9"})

    assert response.status_code == 200
    body = response.json()
    assert body["q"] == "Pro is $9"
    assert body["indexed"] == 1
    assert body["price_usdc"] == "0.005"
    assert len(body["hits"]) == 1
    hit = body["hits"][0]
    assert hit["url"] == "https://example.com/pricing"
    assert hit["title"] == "Pricing"
    assert "$9" in hit["snippet"]
    assert hit["snippet"] != hit["title"]
    assert hit["hash"] == seeded.json()["hash"]
    assert hit["fetched_at"] == seeded.json()["fetched_at"]
    assert fetcher.calls == []


def test_empty_corpus_returns_no_hits() -> None:
    client, _fetcher = _client(pages={})

    response = client.get("/v1/search", params={"q": "anything at all"})

    assert response.status_code == 200
    body = response.json()
    assert body["indexed"] == 0
    assert body["hits"] == []


def test_search_does_not_return_unrelated_pages() -> None:
    client, _fetcher = _client()
    assert client.get("/v1/page", params={"url": "https://example.com/pricing"}).status_code == 200

    response = client.get("/v1/search", params={"q": "kubernetes operators"})

    assert response.status_code == 200
    assert response.json()["indexed"] == 1
    assert response.json()["hits"] == []


def test_title_matches_rank_above_body_only_matches() -> None:
    client, _fetcher = _client(
        {
            "https://example.com/blog": FakePage(
                body=b"<html><head><title>Notes</title></head>"
                b"<body><p>Also mentions background tasks in passing.</p></body></html>"
            ),
            "https://example.com/docs": FakePage(body=DOCS_HTML),
        }
    )
    assert client.get("/v1/page", params={"url": "https://example.com/blog"}).status_code == 200
    assert client.get("/v1/page", params={"url": "https://example.com/docs"}).status_code == 200

    response = client.get("/v1/search", params={"q": "background tasks"})

    urls = [hit["url"] for hit in response.json()["hits"]]
    assert urls[0] == "https://example.com/docs"
    assert "https://example.com/blog" in urls
    assert response.json()["hits"][0]["score"] > response.json()["hits"][1]["score"]


def test_stale_snapshots_can_be_excluded() -> None:
    clock = FakeClock()
    store = MemorySnapshotStore()
    client, _fetcher = _client(store=store, clock=clock)
    assert client.get("/v1/page", params={"url": "https://example.com/pricing"}).status_code == 200
    clock.advance(2_000)

    stale = client.get("/v1/search", params={"q": "pricing", "max_age_s": 900})
    fresh_enough = client.get("/v1/search", params={"q": "pricing", "max_age_s": 10_000})

    assert stale.json()["hits"] == []
    assert [hit["url"] for hit in fresh_enough.json()["hits"]] == [
        "https://example.com/pricing"
    ]


def test_limit_caps_the_hit_list() -> None:
    client, _fetcher = _client(
        {
            "https://example.com/a": FakePage(
                body=b"<html><head><title>Alpha widget</title></head><body>widget</body></html>"
            ),
            "https://example.com/b": FakePage(
                body=b"<html><head><title>Beta widget</title></head><body>widget</body></html>"
            ),
        }
    )
    assert client.get("/v1/page", params={"url": "https://example.com/a"}).status_code == 200
    assert client.get("/v1/page", params={"url": "https://example.com/b"}).status_code == 200

    response = client.get("/v1/search", params={"q": "widget", "limit": 1})

    assert response.status_code == 200
    assert len(response.json()["hits"]) == 1
    assert response.json()["indexed"] == 2


def test_blank_query_is_rejected() -> None:
    client, _fetcher = _client()

    response = client.get("/v1/search", params={"q": "   !!!   "})

    assert response.status_code == 422
