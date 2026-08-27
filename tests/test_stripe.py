from fastapi.testclient import TestClient

from afterimage.app import create_app
from afterimage.keys import MemoryKeyStore
from afterimage.pricing import MISS_ATOMIC
from afterimage.settings import Settings
from tests.fakes import FakeClock, FakeFetcher, FakePage, MemorySnapshotStore
from tests.test_page import PRICING_HTML


class FakeCheckout:
    def __init__(self) -> None:
        self.sessions: list[dict] = []

    async def create_session(self, *, key_id: str, pack: str, cents: int) -> str:
        self.sessions.append({"key_id": key_id, "pack": pack, "cents": cents})
        return f"https://checkout.test/{pack}/{key_id}"


def _stripe_client(keys: MemoryKeyStore | None = None, checkout: FakeCheckout | None = None):
    keys = keys or MemoryKeyStore()
    checkout = checkout or FakeCheckout()
    client = TestClient(
        create_app(
            fetcher=FakeFetcher(
                {"https://example.com/pricing": FakePage(body=PRICING_HTML)}
            ),
            store=MemorySnapshotStore(),
            clock=FakeClock(),
            settings=Settings(
                stripe_secret_key="sk_test_fake",
                public_url="https://afterimage.example",
            ),
            keys=keys,
            checkout=checkout,
        )
    )
    return client, keys, checkout


def test_stripe_mode_rejects_unpaid_calls_with_checkout_pointer() -> None:
    client, _keys, _checkout = _stripe_client()

    response = client.get("/v1/page", params={"url": "https://example.com/pricing"})

    assert response.status_code == 402
    body = response.json()
    assert "checkout" in body["error"].lower() or "/v1/billing/checkout" in str(body)


def test_checkout_mints_a_key_and_webhook_credits_it() -> None:
    client, keys, checkout = _stripe_client()

    created = client.post("/v1/billing/checkout", json={"pack": "starter"})
    assert created.status_code == 200
    payload = created.json()
    api_key = payload["api_key"]
    assert api_key.startswith("ak_")
    assert payload["checkout_url"].startswith("https://checkout.test/")
    assert checkout.sessions[0]["pack"] == "starter"

    key_id = checkout.sessions[0]["key_id"]
    assert keys.balance_for_secret(api_key) == 0
    keys.apply_credit(key_id, micros=5_000_000, stripe_session="cs_test_1")
    assert keys.balance_for_secret(api_key) == 5_000_000

    paid = client.get(
        "/v1/page",
        params={"url": "https://example.com/pricing"},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert paid.status_code == 200
    assert paid.json()["cache"] == "miss"
    assert keys.balance_for_secret(api_key) == 5_000_000 - int(MISS_ATOMIC)


def test_empty_balance_is_rejected() -> None:
    client, keys, _checkout = _stripe_client()
    created = client.post("/v1/billing/checkout", json={"pack": "starter"}).json()
    response = client.get(
        "/v1/page",
        params={"url": "https://example.com/pricing"},
        headers={"Authorization": f"Bearer {created['api_key']}"},
    )
    assert response.status_code == 402
    assert keys.balance_for_secret(created["api_key"]) == 0
