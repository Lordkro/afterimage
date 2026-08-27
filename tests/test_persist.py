from pathlib import Path

from fastapi.testclient import TestClient

from afterimage.app import create_app
from afterimage.store import SqliteSnapshotStore
from tests.fakes import FakeClock, FakeFetcher, FakePage
from tests.test_page import PRICING_HTML


def test_snapshots_persist_across_app_instances(tmp_path: Path) -> None:
    path = str(tmp_path / "afterimage.db")
    clock = FakeClock()
    url = "https://example.com/pricing"

    first = TestClient(
        create_app(
            fetcher=FakeFetcher({url: FakePage(body=PRICING_HTML)}),
            store=SqliteSnapshotStore(path),
            clock=clock,
        )
    )
    miss = first.get("/v1/page", params={"url": url})
    assert miss.json()["cache"] == "miss"

    second = TestClient(
        create_app(
            fetcher=FakeFetcher({}),
            store=SqliteSnapshotStore(path),
            clock=clock,
        )
    )
    hit = second.get("/v1/page", params={"url": url})
    assert hit.status_code == 200
    assert hit.json()["cache"] == "hit"
    assert hit.json()["hash"] == miss.json()["hash"]
    assert "Pro is $9" in hit.json()["text"]


def test_search_survives_across_app_instances(tmp_path: Path) -> None:
    path = str(tmp_path / "afterimage.db")
    url = "https://example.com/pricing"
    clock = FakeClock()

    first = TestClient(
        create_app(
            fetcher=FakeFetcher({url: FakePage(body=PRICING_HTML)}),
            store=SqliteSnapshotStore(path),
            clock=clock,
        )
    )
    assert first.get("/v1/page", params={"url": url}).status_code == 200

    second = TestClient(
        create_app(
            fetcher=FakeFetcher({}),
            store=SqliteSnapshotStore(path),
            clock=clock,
        )
    )
    response = second.get("/v1/search", params={"q": "Pro is $9"})
    assert response.status_code == 200
    body = response.json()
    assert body["indexed"] == 1
    assert body["hits"][0]["url"] == url
    assert "$9" in body["hits"][0]["snippet"]
