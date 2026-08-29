from fastapi.testclient import TestClient

from afterimage.app import create_app
from afterimage.pricing import MISS_ATOMIC
from afterimage.settings import Settings


def test_llms_txt_tells_an_agent_how_to_call_afterimage() -> None:
    client = TestClient(create_app())

    response = client.get("/llms.txt")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    text = response.text
    assert "AfterImage" in text
    assert "/v1/page" in text
    assert "Accept-Language: en-US" in text
    assert "never Cookie" in text
    assert "max_age_s" in text
    assert "/v1/billing/checkout" in text
    assert "Authorization" in text
    assert "/mcp" in text
    assert "/v1/search" in text
    assert "sha256" in text
    assert "x402" in text.lower()
    assert "/v1/stats" in text
    assert "robots.txt" in text.lower() or "robots.txt" in text
    assert "does not currently honor origin" in text.lower()
    assert "robots.txt" in text.lower()
    assert "noarchive" in text.lower()
    assert "no-store" in text.lower()
    assert "always bill" in text.lower() or "live-fetch" in text.lower()
    assert "volatile" in text.lower()
    assert "10-day" in text or "10 days" in text
    assert "status pages" in text.lower()
    assert "removal@afterimage.page" in text


def test_openapi_documents_the_page_endpoint() -> None:
    client = TestClient(create_app())

    spec = client.get("/openapi.json").json()

    assert "/v1/page" in spec["paths"]
    assert "get" in spec["paths"]["/v1/page"]
    params = spec["paths"]["/v1/page"]["get"]["parameters"]
    names = {p["name"] for p in params}
    assert "url" in names
    assert "max_age_s" in names
    assert "/v1/search" in spec["paths"]
    search_params = {p["name"] for p in spec["paths"]["/v1/search"]["get"]["parameters"]}
    assert "q" in search_params
    schemes = (spec.get("components") or {}).get("securitySchemes") or {}
    assert schemes
    assert "/v1/billing/webhook" not in spec["paths"]
    checkout = spec["paths"]["/v1/billing/checkout"]["post"]
    body = checkout.get("requestBody") or {}
    blob = str(body).lower()
    assert "pack" in blob
    assert "402" in str(spec["paths"]["/mcp"])


def test_x402_well_known_advertises_the_page_resource() -> None:
    client = TestClient(create_app())

    response = client.get("/.well-known/x402")

    assert response.status_code == 200
    body = response.json()
    assert body["x402Version"] == 2
    resources = body.get("resources") or body.get("accepts")
    assert resources
    blob = str(body).lower()
    assert "/v1/page" in blob
    assert "/v1/search" in blob
    assert "usdc" in blob
    cache = response.headers.get("cache-control", "").lower()
    assert "max-age=3600" not in cache


def test_agent_card_is_a2a_discoverable() -> None:
    client = TestClient(create_app())

    response = client.get("/.well-known/agent-card.json")

    assert response.status_code == 200
    card = response.json()
    assert card["name"] == "AfterImage"
    assert "skills" in card
    skill_ids = {s["id"] for s in card["skills"]}
    assert "get_page" in skill_ids
    assert "search_pages" in skill_ids
    assert card.get("securitySchemes") or card.get("security")
    assert "paid" in str(card).lower() or "api key" in str(card).lower() or "402" in str(card)


def test_x402_well_known_advertises_one_amount_per_resource() -> None:
    client = TestClient(
        create_app(
            settings=Settings(
                pay_to="0x1111111111111111111111111111111111111111",
                public_url="https://afterimage.page",
            )
        )
    )
    resources = client.get("/.well-known/x402").json()["resources"]
    by_url = {item["url"]: item for item in resources}
    page = by_url["https://afterimage.page/v1/page"]
    assert [a["amount"] for a in page["accepts"]] == [MISS_ATOMIC]
    mcp = by_url["https://afterimage.page/mcp"]
    assert len(mcp["accepts"]) == 1


def test_robots_txt_is_published() -> None:
    text = TestClient(create_app()).get("/robots.txt").text
    assert "llms.txt" in text
    assert "User-agent" in text
