from fastapi.testclient import TestClient

from afterimage.app import create_app
from afterimage.origin_cache import origin_cache_policy
from tests.fakes import FakeClock, FakeFetcher, FakePage, MemorySnapshotStore
from tests.test_page import PRICING_HTML


def test_no_store_is_not_persisted() -> None:
    policy = origin_cache_policy(headers={"cache-control": "no-store"})
    assert policy.persist is False
    assert policy.reason == "no-store"


def test_private_is_not_persisted_in_a_shared_cache() -> None:
    policy = origin_cache_policy(headers={"cache-control": "private, max-age=3600"})
    assert policy.persist is False
    assert policy.reason == "private"


def test_s_maxage_wins_for_shared_cache() -> None:
    policy = origin_cache_policy(headers={"cache-control": "max-age=300, s-maxage=60"})
    assert policy.persist is True
    assert policy.max_age_s == 60


def test_max_age_is_parsed() -> None:
    policy = origin_cache_policy(headers={"cache-control": "public, max-age=60"})
    assert policy.persist is True
    assert policy.max_age_s == 60
    assert policy.reason is None


def test_no_cache_is_stored_but_never_fresh() -> None:
    policy = origin_cache_policy(headers={"cache-control": "no-cache, max-age=600"})
    assert policy.persist is True
    assert policy.max_age_s == 0


def test_must_revalidate_without_lifetime_is_never_fresh() -> None:
    policy = origin_cache_policy(headers={"cache-control": "must-revalidate"})
    assert policy.persist is True
    assert policy.max_age_s == 0


def test_age_is_subtracted_from_lifetime() -> None:
    policy = origin_cache_policy(headers={"cache-control": "max-age=600", "age": "550"})
    assert policy.persist is True
    assert policy.max_age_s == 50


def test_expires_is_used_when_cache_control_is_absent() -> None:
    policy = origin_cache_policy(
        headers={
            "date": "Sat, 29 Aug 2026 12:00:00 GMT",
            "expires": "Sat, 29 Aug 2026 12:01:00 GMT",
        }
    )
    assert policy.persist is True
    assert policy.max_age_s == 60


def test_vary_star_is_not_persisted() -> None:
    policy = origin_cache_policy(headers={"vary": "*"})
    assert policy.persist is False
    assert policy.reason == "vary"


def test_no_store_page_is_returned_with_reason() -> None:
    store = MemorySnapshotStore()
    client = TestClient(
        create_app(
            fetcher=FakeFetcher(
                {
                    "https://example.com/priv": FakePage(
                        body=PRICING_HTML,
                        headers={"cache-control": "no-store"},
                    )
                }
            ),
            store=store,
        )
    )
    body = client.get("/v1/page", params={"url": "https://example.com/priv"}).json()
    assert body["stored"] is False
    assert body["stored_reason"] == "no-store"
    assert client.get("/v1/page", params={"url": "https://example.com/priv"}).json()[
        "cache"
    ] == "miss"


def test_origin_max_age_caps_reuse() -> None:
    clock = FakeClock()
    store = MemorySnapshotStore()
    client = TestClient(
        create_app(
            fetcher=FakeFetcher(
                {
                    "https://example.com/short": FakePage(
                        body=PRICING_HTML,
                        headers={"cache-control": "max-age=30"},
                    )
                }
            ),
            store=store,
            clock=clock,
        )
    )
    miss = client.get(
        "/v1/page",
        params={"url": "https://example.com/short", "max_age_s": 900},
    ).json()
    assert miss["cache"] == "miss"
    assert miss["stored"] is True
    assert miss["origin_max_age_s"] == 30
    clock.advance(31)
    again = client.get(
        "/v1/page",
        params={"url": "https://example.com/short", "max_age_s": 900},
    ).json()
    assert again["cache"] == "miss"


def test_age_shortens_stored_freshness() -> None:
    clock = FakeClock()
    client = TestClient(
        create_app(
            fetcher=FakeFetcher(
                {
                    "https://example.com/cdn": FakePage(
                        body=PRICING_HTML,
                        headers={"cache-control": "max-age=600", "age": "550"},
                    )
                }
            ),
            store=MemorySnapshotStore(),
            clock=clock,
        )
    )
    miss = client.get(
        "/v1/page",
        params={"url": "https://example.com/cdn", "max_age_s": 900},
    ).json()
    assert miss["stored"] is True
    assert miss["origin_max_age_s"] == 50
    clock.advance(51)
    again = client.get(
        "/v1/page",
        params={"url": "https://example.com/cdn", "max_age_s": 900},
    ).json()
    assert again["cache"] == "miss"


def test_no_cache_never_becomes_a_hit() -> None:
    client = TestClient(
        create_app(
            fetcher=FakeFetcher(
                {
                    "https://example.com/reval": FakePage(
                        body=PRICING_HTML,
                        headers={"cache-control": "no-cache"},
                    )
                }
            ),
            store=MemorySnapshotStore(),
        )
    )
    first = client.get(
        "/v1/page",
        params={"url": "https://example.com/reval", "max_age_s": 900},
    ).json()
    assert first["stored"] is True
    assert first["origin_max_age_s"] == 0
    second = client.get(
        "/v1/page",
        params={"url": "https://example.com/reval", "max_age_s": 900},
    ).json()
    assert second["cache"] == "miss"


def test_vary_star_is_returned_with_reason() -> None:
    body = (
        TestClient(
            create_app(
                fetcher=FakeFetcher(
                    {
                        "https://example.com/vary": FakePage(
                            body=PRICING_HTML,
                            headers={"vary": "*"},
                        )
                    }
                ),
                store=MemorySnapshotStore(),
            )
        )
        .get("/v1/page", params={"url": "https://example.com/vary"})
        .json()
    )
    assert body["stored"] is False
    assert body["stored_reason"] == "vary"
