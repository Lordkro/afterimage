import base64
import json

from fastapi.testclient import TestClient

import httpx

from afterimage.app import create_app
from afterimage.facilitator import facilitator_error
from afterimage.pricing import HIT_ATOMIC, MISS_ATOMIC, SEARCH_ATOMIC
from afterimage.settings import Settings
from tests.fakes import FakeClock, FakeFetcher, FakePage, MemorySnapshotStore
from tests.test_page import PRICING_HTML

PAY_TO = "0x1111111111111111111111111111111111111111"


class AcceptingFacilitator:
    async def settle(self, payload: dict, requirements: dict) -> dict:
        return {
            "success": True,
            "transaction": "0xabc",
            "network": requirements["accepts"][0]["network"],
            "payer": "0x2222222222222222222222222222222222222222",
        }


def _paid_client(**kwargs) -> TestClient:
    return TestClient(
        create_app(
            fetcher=kwargs.get(
                "fetcher",
                FakeFetcher({"https://example.com/pricing": FakePage(body=PRICING_HTML)}),
            ),
            store=kwargs.get("store", MemorySnapshotStore()),
            clock=kwargs.get("clock", FakeClock()),
            settings=Settings(pay_to=PAY_TO, public_url="https://afterimage.example"),
            facilitator=kwargs.get("facilitator", AcceptingFacilitator()),
        )
    )


def _decode_payment_required(response) -> dict:
    raw = response.headers.get("payment-required")
    assert raw, response.headers
    padded = raw + "=" * (-len(raw) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def test_paid_mode_challenges_even_when_query_params_are_missing() -> None:
    client = _paid_client()

    response = client.get("/v1/page")

    assert response.status_code == 402
    required = _decode_payment_required(response)
    assert required["extensions"]["bazaar"]["info"]["input"]["method"] == "GET"


def test_paid_mode_challenges_unpaid_fetch_at_miss_price() -> None:
    client = _paid_client()

    response = client.get("/v1/page", params={"url": "https://example.com/pricing"})

    assert response.status_code == 402
    required = _decode_payment_required(response)
    assert required["x402Version"] == 2
    amounts = {item["amount"] for item in required["accepts"]}
    assert MISS_ATOMIC in amounts
    assert required["resource"]["url"].endswith("/v1/page")
    assert required["accepts"][0]["extra"]["name"] == "USD Coin"
    assert required["accepts"][0]["extra"]["version"] == "2"
    bazaar = required["extensions"]["bazaar"]
    assert bazaar["info"]["input"]["type"] == "http"
    assert bazaar["info"]["input"]["method"] == "GET"
    assert "url" in bazaar["info"]["input"]["queryParams"]
    assert "url" in bazaar["schema"]["properties"]["input"]["properties"]["queryParams"]["properties"]
    resource = required["resource"]
    assert resource["serviceName"] == "AfterImage"
    assert "snapshot" in resource["tags"]
    assert resource["iconUrl"].endswith("/icon.svg")
    assert "any public URL" in resource["description"]


def test_paid_mode_challenges_cache_hit_at_hit_price() -> None:
    store = MemorySnapshotStore()
    clock = FakeClock()
    fetcher = FakeFetcher({"https://example.com/pricing": FakePage(body=PRICING_HTML)})
    free = TestClient(
        create_app(fetcher=fetcher, store=store, clock=clock, settings=Settings())
    )
    assert free.get("/v1/page", params={"url": "https://example.com/pricing"}).status_code == 200

    client = TestClient(
        create_app(
            fetcher=fetcher,
            store=store,
            clock=clock,
            settings=Settings(pay_to=PAY_TO, public_url="https://afterimage.example"),
            facilitator=AcceptingFacilitator(),
        )
    )
    response = client.get("/v1/page", params={"url": "https://example.com/pricing"})

    assert response.status_code == 402
    required = _decode_payment_required(response)
    amounts = {item["amount"] for item in required["accepts"]}
    assert amounts == {HIT_ATOMIC}


def test_settled_payment_returns_the_snapshot() -> None:
    client = _paid_client()
    payload = {
        "x402Version": 2,
        "accepted": {"scheme": "exact", "amount": MISS_ATOMIC},
        "payload": {"test": True},
    }
    token = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    response = client.get(
        "/v1/page",
        params={"url": "https://example.com/pricing"},
        headers={"PAYMENT-SIGNATURE": token},
    )

    assert response.status_code == 200
    assert response.json()["cache"] == "miss"
    assert response.headers.get("payment-response")


def test_paid_mode_challenges_search_at_search_price() -> None:
    store = MemorySnapshotStore()
    clock = FakeClock()
    fetcher = FakeFetcher({"https://example.com/pricing": FakePage(body=PRICING_HTML)})
    free = TestClient(
        create_app(fetcher=fetcher, store=store, clock=clock, settings=Settings())
    )
    assert free.get("/v1/page", params={"url": "https://example.com/pricing"}).status_code == 200

    client = TestClient(
        create_app(
            fetcher=fetcher,
            store=store,
            clock=clock,
            settings=Settings(pay_to=PAY_TO, public_url="https://afterimage.example"),
            facilitator=AcceptingFacilitator(),
        )
    )
    response = client.get("/v1/search", params={"q": "Pro is $9"})

    assert response.status_code == 402
    required = _decode_payment_required(response)
    amounts = {item["amount"] for item in required["accepts"]}
    assert amounts == {SEARCH_ATOMIC}
    assert required["resource"]["url"].endswith("/v1/search")
    assert required["extensions"]["bazaar"]["info"]["input"]["queryParams"]["q"]


def test_facilitator_error_includes_response_body() -> None:
    response = httpx.Response(
        500,
        text='{"error":"No facilitator registered for scheme: exact and network: eip155:8453"}',
    )
    assert "eip155:8453" in facilitator_error("verify", response)
    assert "500" in facilitator_error("verify", response)
