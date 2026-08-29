from fastapi.testclient import TestClient

from afterimage.app import create_app
from afterimage.robots_archive import forbids_archive
from tests.fakes import FakeFetcher, FakePage, MemorySnapshotStore


def test_x_robots_tag_noarchive_forbids_store() -> None:
    assert forbids_archive(
        headers={"x-robots-tag": "noindex, noarchive"},
        body=b"<html><p>hi</p></html>",
        content_type="text/html",
    )


def test_meta_robots_noarchive_forbids_store() -> None:
    html = b'<html><head><meta name="robots" content="noarchive"></head><body>secret</body></html>'
    assert forbids_archive(headers={}, body=html, content_type="text/html")


def test_ordinary_html_may_be_stored() -> None:
    assert not forbids_archive(
        headers={},
        body=b"<html><head><title>ok</title></head><body><p>public</p></body></html>",
        content_type="text/html",
    )


def test_noarchive_page_is_returned_but_not_stored() -> None:
    html = (
        b"<html><head><meta name=\"robots\" content=\"noarchive\">"
        b"</head><body><p>Secret recipe</p></body></html>"
    )
    store = MemorySnapshotStore()
    client = TestClient(
        create_app(
            fetcher=FakeFetcher(
                {"https://example.com/secret": FakePage(body=html)}
            ),
            store=store,
        )
    )
    body = client.get(
        "/v1/page", params={"url": "https://example.com/secret"}
    ).json()
    assert "Secret recipe" in body["text"]
    assert body["stored"] is False
    again = client.get(
        "/v1/page", params={"url": "https://example.com/secret"}
    ).json()
    assert again["cache"] == "miss"


def test_x_robots_tag_noarchive_is_not_stored() -> None:
    store = MemorySnapshotStore()
    client = TestClient(
        create_app(
            fetcher=FakeFetcher(
                {
                    "https://example.com/hdr": FakePage(
                        body=b"<html><body><p>Leave me</p></body></html>",
                        headers={"x-robots-tag": "noarchive"},
                    )
                }
            ),
            store=store,
        )
    )
    body = client.get("/v1/page", params={"url": "https://example.com/hdr"}).json()
    assert body["stored"] is False
    assert "Leave me" in body["text"]
