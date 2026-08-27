from __future__ import annotations

from typing import Any

from already import __version__
from already.models import Clock, Fetcher, SnapshotStore
from already.pages import DEFAULT_MAX_AGE_S, snapshot_page
from already.search import DEFAULT_SEARCH_LIMIT, MAX_SEARCH_LIMIT, search_corpus

SEARCH_PAGES_SCHEMA = {
    "type": "object",
    "properties": {
        "q": {
            "type": "string",
            "description": "Search the already-fetched corpus. Does not hit the live web.",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": MAX_SEARCH_LIMIT,
            "default": DEFAULT_SEARCH_LIMIT,
        },
        "max_age_s": {
            "type": "integer",
            "minimum": 0,
            "description": "Only return snapshots no older than this many seconds.",
        },
    },
    "required": ["q"],
}

GET_PAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "Absolute http(s) URL to snapshot.",
        },
        "max_age_s": {
            "type": "integer",
            "minimum": 0,
            "default": DEFAULT_MAX_AGE_S,
            "description": "Reuse a cached snapshot if it is no older than this many seconds.",
        },
    },
    "required": ["url"],
}


def tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "get_page",
            "description": (
                "Return a readable snapshot of a public web page, reusing a fresh-enough "
                "cached copy when one exists. Includes sha256 hash, fetched_at, and cache hit/miss."
            ),
            "inputSchema": GET_PAGE_SCHEMA,
        },
        {
            "name": "search_pages",
            "description": (
                "Search pages Already has already fetched. Returns urls, titles, snippets, "
                "hashes, and fetched_at. Use this instead of scraping when another agent "
                "may have looked already. Then call get_page for the full snapshot."
            ),
            "inputSchema": SEARCH_PAGES_SCHEMA,
        },
    ]


def initialize_result() -> dict[str, Any]:
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {"name": "already", "version": __version__},
        "instructions": (
            "Call search_pages to query the corpus of already-fetched pages. "
            "Call get_page with a public http(s) url when you need a specific page's "
            "readable text and can accept a snapshot up to max_age_s seconds old."
        ),
    }


async def handle_rpc(
    message: dict[str, Any],
    *,
    store: SnapshotStore,
    fetcher: Fetcher,
    clock: Clock,
) -> dict[str, Any] | None:
    if message.get("jsonrpc") != "2.0":
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {"code": -32600, "message": "jsonrpc must be 2.0"},
        }
    method = message.get("method")
    rpc_id = message.get("id")
    params = message.get("params") or {}

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": initialize_result()}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": tools()}}
    if method == "tools/call":
        return await _call_tool(
            rpc_id, params, store=store, fetcher=fetcher, clock=clock
        )
    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "error": {"code": -32601, "message": f"unknown method {method}"},
    }


async def _call_tool(
    rpc_id: Any,
    params: dict[str, Any],
    *,
    store: SnapshotStore,
    fetcher: Fetcher,
    clock: Clock,
) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") or {}
    try:
        if name == "get_page":
            payload = await _get_page(arguments, store=store, fetcher=fetcher, clock=clock)
        elif name == "search_pages":
            payload = await _search_pages(arguments, store=store, clock=clock)
        else:
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32601, "message": f"unknown tool {name}"},
            }
    except Exception as exc:
        message = getattr(exc, "detail", str(exc))
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "isError": True,
                "content": [{"type": "text", "text": str(message)}],
            },
        }
    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "result": {
            "content": [{"type": "text", "text": _json(payload)}],
            "structuredContent": payload,
            "isError": False,
        },
    }


async def _get_page(
    arguments: dict[str, Any],
    *,
    store: SnapshotStore,
    fetcher: Fetcher,
    clock: Clock,
) -> dict[str, Any]:
    url = arguments.get("url")
    if not url:
        raise ValueError("url is required")
    max_age_s = int(arguments.get("max_age_s", DEFAULT_MAX_AGE_S))
    page = await snapshot_page(
        url,
        max_age_s=max_age_s,
        store=store,
        fetcher=fetcher,
        clock=clock,
    )
    return page.model_dump()


async def _search_pages(
    arguments: dict[str, Any],
    *,
    store: SnapshotStore,
    clock: Clock,
) -> dict[str, Any]:
    q = arguments.get("q")
    if not q:
        raise ValueError("q is required")
    limit = int(arguments.get("limit", DEFAULT_SEARCH_LIMIT))
    max_age_s = arguments.get("max_age_s")
    result = await search_corpus(
        q,
        store=store,
        clock=clock,
        limit=limit,
        max_age_s=int(max_age_s) if max_age_s is not None else None,
    )
    return result.model_dump()


def _json(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload)
