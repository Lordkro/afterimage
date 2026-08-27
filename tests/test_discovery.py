from fastapi.testclient import TestClient

from already.app import create_app


def test_llms_txt_tells_an_agent_how_to_call_already() -> None:
    client = TestClient(create_app())

    response = client.get("/llms.txt")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    text = response.text
    assert "Already" in text
    assert "/v1/page" in text
    assert "max_age_s" in text
    assert "x402" in text.lower()
    assert "/mcp" in text
    assert "/v1/search" in text
    assert "sha256" in text


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


def test_agent_card_is_a2a_discoverable() -> None:
    client = TestClient(create_app())

    response = client.get("/.well-known/agent-card.json")

    assert response.status_code == 200
    card = response.json()
    assert card["name"] == "Already"
    assert "skills" in card
    skill_ids = {s["id"] for s in card["skills"]}
    assert "get_page" in skill_ids
    assert "search_pages" in skill_ids
