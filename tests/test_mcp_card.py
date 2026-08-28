from fastapi.testclient import TestClient

from afterimage.app import create_app
from afterimage.settings import Settings


def _client() -> TestClient:
    return TestClient(
        create_app(settings=Settings(public_url="https://afterimage.page"))
    )


def test_well_known_mcp_json_advertises_the_remote_server() -> None:
    response = _client().get("/.well-known/mcp.json")

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    card = response.json()
    assert card["name"] == "page.afterimage/afterimage"
    assert card["title"] == "AfterImage"
    assert "shared cop" in card["description"].lower() or "snapshot" in card["description"].lower()
    remotes = card["remotes"]
    assert remotes[0]["type"] == "streamable-http"
    assert remotes[0]["url"] == "https://afterimage.page/mcp"
    assert response.headers.get("access-control-allow-origin") == "*"


def test_mcp_server_card_aliases_and_ai_catalog_point_at_the_same_server() -> None:
    client = _client()
    card = client.get("/.well-known/mcp.json").json()

    for path in ("/mcp/server-card", "/.well-known/mcp/server-card.json"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.json()["remotes"] == card["remotes"]

    catalog = client.get("/.well-known/ai-catalog.json")
    assert catalog.status_code == 200
    entries = catalog.json()["entries"]
    assert entries[0]["type"] == "application/mcp-server-card+json"
    assert entries[0]["url"] == "https://afterimage.page/mcp/server-card"


def test_mcp_registry_auth_proves_domain_ownership() -> None:
    response = _client().get("/.well-known/mcp-registry-auth")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    text = response.text.strip()
    assert text.startswith("v=MCPv1; k=ed25519; p=")
    assert len(text.split("p=", 1)[1]) > 20
