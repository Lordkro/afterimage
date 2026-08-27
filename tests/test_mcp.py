import json

from fastapi.testclient import TestClient

from already.app import create_app
from tests.fakes import FakeFetcher, FakePage, MemorySnapshotStore
from tests.test_page import PRICING_HTML


def _client() -> TestClient:
    return TestClient(
        create_app(
            fetcher=FakeFetcher(
                {"https://example.com/pricing": FakePage(body=PRICING_HTML)}
            ),
            store=MemorySnapshotStore(),
        )
    )


def test_mcp_initialize_identifies_already() -> None:
    client = _client()

    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        },
    )

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["serverInfo"]["name"] == "already"
    assert "tools" in result["capabilities"]


def test_mcp_lists_get_page() -> None:
    client = _client()

    response = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    )

    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    by_name = {tool["name"]: tool for tool in tools}
    assert "get_page" in by_name
    assert "url" in by_name["get_page"]["inputSchema"]["properties"]


def test_mcp_get_page_returns_a_snapshot() -> None:
    client = _client()

    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_page",
                "arguments": {"url": "https://example.com/pricing", "max_age_s": 900},
            },
        },
    )

    assert response.status_code == 200
    result = response.json()["result"]
    assert result.get("isError") in {None, False}
    payload = json.loads(result["content"][0]["text"])
    assert payload["cache"] == "miss"
    assert "Pro is $9 per month." in payload["text"]
    assert payload["hash"].startswith("sha256:")


def test_mcp_lists_search_pages() -> None:
    client = _client()

    response = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    )

    tools = {tool["name"]: tool for tool in response.json()["result"]["tools"]}
    assert "search_pages" in tools
    assert "q" in tools["search_pages"]["inputSchema"]["properties"]


def test_mcp_search_pages_returns_corpus_hits() -> None:
    client = _client()
    assert client.get("/v1/page", params={"url": "https://example.com/pricing"}).status_code == 200

    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "search_pages",
                "arguments": {"q": "Pro is $9"},
            },
        },
    )

    assert response.status_code == 200
    result = response.json()["result"]
    assert result.get("isError") in {None, False}
    payload = json.loads(result["content"][0]["text"])
    assert payload["hits"][0]["url"] == "https://example.com/pricing"
    assert "$9" in payload["hits"][0]["snippet"]
