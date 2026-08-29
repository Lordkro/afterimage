import asyncio
from datetime import timedelta

from fastapi.testclient import TestClient

from afterimage.app import create_app
from afterimage.landing import fresh_label, freshness_pct, prefers_html
from afterimage.models import Snapshot
from afterimage.settings import Settings
from tests.fakes import FakeClock, MemorySnapshotStore


def test_icon_svg_is_served() -> None:
    client = TestClient(create_app())
    response = client.get("/icon.svg")
    assert response.status_code == 200
    assert "svg" in response.headers["content-type"]
    assert "<svg" in response.text


def test_root_is_a_human_landing_page() -> None:
    client = TestClient(
        create_app(
            settings=Settings(public_url="https://afterimage.page"),
            store=MemorySnapshotStore(),
        )
    )

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    text = response.text
    assert "<html" in text.lower()
    assert "AfterImage" in text
    assert "llms.txt" in text
    assert "$5" in text
    assert "/v1/billing/checkout" in text
    assert "/v1/search" in text
    assert "https://afterimage.page" in text
    assert "Authorization" in text
    assert 'id="keybox"' not in text
    assert 'href="#"' not in text
    assert "AfterImageAfterImage" not in text
    assert "Caps:" in text
    assert "evicted after 10 days" in text
    assert "/icon.svg" in text
    assert "100,000" in text
    assert "About 5,000" not in text
    assert "{{" not in text
    assert 'data-pack="starter"' in text
    assert "Buy $5 credits" in text
    assert "/v1/stats" in text
    assert "in the library" in text
    assert "Fresh copies of the pages models get wrong." in text
    assert "shared copy of the public web" not in text
    assert "https://platform.openai.com/docs/pricing" in text
    assert "fastapi.tiangolo.com" not in text
    assert "missing_key" in text
    assert "unknown_key" in text
    assert "unfunded_key" in text
    assert "insufficient_credits" in text
    assert "missing or empty" not in text
    assert 'id="fresh-label"' in text
    featured = text[text.find('class="pack featured"') :]
    featured = featured[: featured.find("</article>") + 10]
    assert "Builder" in featured
    assert "Starter" not in featured


def test_freshness_pct_is_age_against_ttl_not_fullness() -> None:
    ttl = 10 * 24 * 60 * 60
    assert freshness_pct(indexed=0, oldest_age_s=None, ttl_s=ttl) == 0
    assert freshness_pct(indexed=157, oldest_age_s=0, ttl_s=ttl) == 100
    assert freshness_pct(indexed=157, oldest_age_s=ttl // 2, ttl_s=ttl) == 50
    assert freshness_pct(indexed=157, oldest_age_s=ttl, ttl_s=ttl) == 0
    assert fresh_label(indexed=0, oldest_age_s=None, ttl_s=ttl, ttl_days=10) == "empty"
    assert (
        fresh_label(indexed=157, oldest_age_s=ttl // 2, ttl_s=ttl, ttl_days=10)
        == "oldest has 5 of 10 days left"
    )


def test_landing_meter_is_oldest_copy_freshness() -> None:
    store = MemorySnapshotStore()
    clock = FakeClock()
    fetched = clock.now() - timedelta(days=5)
    asyncio.run(
        store.put(
            Snapshot(
                url="https://platform.openai.com/docs/pricing",
                final_url="https://platform.openai.com/docs/pricing",
                status=200,
                title="Pricing",
                text="Input, cached input, and output are billed per 1M tokens.",
                content_hash="sha256:" + "a" * 64,
                fetched_at=fetched,
                content_type="text/html",
            )
        )
    )
    client = TestClient(
        create_app(
            settings=Settings(public_url="https://afterimage.page"),
            store=store,
            clock=clock,
        )
    )

    text = client.get("/").text

    assert 'style="width:50%"' in text
    assert "oldest has 5 of 10 days left" in text
    assert 'style="width:0%"' not in text
    assert "pages of" not in text


def test_prefers_html_follows_accept_order() -> None:
    assert prefers_html("text/html,application/xhtml+xml")
    assert not prefers_html("*/*")
    assert not prefers_html("application/json")
    assert not prefers_html("application/json, text/html")
    assert prefers_html("text/html, application/json")
