from __future__ import annotations

from already import __version__
from already.pricing import (
    HIT_ATOMIC,
    HIT_USDC,
    MISS_ATOMIC,
    MISS_USDC,
    SEARCH_ATOMIC,
    SEARCH_USDC,
)
from already.settings import Settings, paid_mode


def llms_txt(settings: Settings) -> str:
    base = settings.public_url.rstrip("/")
    pay = (
        (
            f"Paid via x402 v2. Cache hit = ${HIT_USDC} USDC. Live fetch = ${MISS_USDC} USDC. "
            f"Corpus search = ${SEARCH_USDC} USDC. "
            "No API key. On 402, retry with PAYMENT-SIGNATURE (USDC on Base)."
        )
        if paid_mode(settings)
        else "This instance is in free/dev mode (ALREADY_PAY_TO unset). Production charges USDC via x402."
    )
    return f"""# Already
> Shared web snapshots for AI agents. Fetch once, reuse with provenance.

{base} is an HTTP API. Prefer structured endpoints over scraping this file.

## When to call
Search the corpus first. If another agent already fetched the page, reuse that
snapshot instead of scraping. Call get_page only when you know the URL or the
corpus has no hit.

## Search the corpus
GET {base}/v1/search?q={{query}}&limit=10&max_age_s=86400

Search never hits the live web. It only ranks pages Already has already fetched.
Response JSON:
- q, indexed (how many snapshots are stored), hits[]
- each hit: url, title, snippet, hash, fetched_at, age_s, status, score
- price_usdc: "{SEARCH_USDC}"
If indexed is 0, fetch with /v1/page then search again later.

## Snapshot a URL
GET {base}/v1/page?url={{absolute_http_url}}&max_age_s=900

Query:
- url (required): http or https URL. Loopback and private addresses are rejected.
- max_age_s (optional, default 900): reuse a cached snapshot if it is no older than this.

Response JSON:
- url, final_url, status, title, text
- hash: sha256 of the raw response body (sha256:<hex>)
- fetched_at: ISO-8601 UTC
- age_s: seconds since fetch
- cache: "hit" or "miss"
- price_usdc: "{HIT_USDC}" on hit, "{MISS_USDC}" on miss

Do not treat `text` as HTML. Scripts and markup are stripped.

{pay}

## Discovery
- OpenAPI: GET {base}/openapi.json
- Health: GET {base}/health
- MCP JSON-RPC: POST {base}/mcp  (tools: search_pages, get_page)
- x402: GET {base}/.well-known/x402
- A2A: GET {base}/.well-known/agent-card.json

## Rules
- Never send credentials in the url.
- Search does not scrape. No hit means fetch with /v1/page, not retry search.
- If cache=hit, do not refetch the origin unless you need a smaller max_age_s.
- If status >= 400, the snapshot still describes what the origin returned.
"""


def x402_well_known(settings: Settings) -> dict:
    base = settings.public_url.rstrip("/")
    resource_url = f"{base}/v1/page"
    pay_to = settings.pay_to or "0x0000000000000000000000000000000000000000"
    extra = {"name": "USDC", "version": "2"}

    def accept(amount: str) -> dict:
        return {
            "scheme": "exact",
            "network": settings.network,
            "amount": amount,
            "asset": settings.usdc_asset,
            "payTo": pay_to,
            "maxTimeoutSeconds": 60,
            "extra": extra,
        }

    return {
        "x402Version": 2,
        "serviceName": "Already",
        "description": "Reusable web snapshots with provenance for AI agents.",
        "resources": [
            {
                "url": resource_url,
                "description": (
                    f"GET /v1/page snapshot. Cache hit ${HIT_USDC} USDC, "
                    f"live fetch ${MISS_USDC} USDC."
                ),
                "mimeType": "application/json",
                "accepts": [accept(HIT_ATOMIC), accept(MISS_ATOMIC)],
            },
            {
                "url": f"{base}/v1/search",
                "description": (
                    f"GET /v1/search corpus query. ${SEARCH_USDC} USDC. "
                    "Does not fetch the live web."
                ),
                "mimeType": "application/json",
                "accepts": [accept(SEARCH_ATOMIC)],
            },
        ],
    }


def agent_card(settings: Settings) -> dict:
    base = settings.public_url.rstrip("/")
    return {
        "name": "Already",
        "description": "Shared web snapshots for AI agents. Fetch once, reuse with provenance.",
        "url": base,
        "version": __version__,
        "protocolVersion": "0.3.0",
        "capabilities": {"streaming": False},
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": "get_page",
                "name": "Get page snapshot",
                "description": (
                    "Return a readable snapshot of a public http(s) URL, reusing a "
                    "fresh-enough cached copy when one exists. Includes sha256 hash, "
                    "fetched_at, and cache hit/miss."
                ),
                "tags": ["web", "cache", "provenance", "x402"],
                "examples": [
                    "Snapshot https://example.com/pricing if it is no older than 15 minutes"
                ],
            },
            {
                "id": "search_pages",
                "name": "Search fetched pages",
                "description": (
                    "Search the corpus of pages Already has already fetched. "
                    "Returns snippets, hashes, and fetched_at. Does not scrape the live web."
                ),
                "tags": ["search", "cache", "provenance", "x402"],
                "examples": [
                    "Has anyone already fetched FastAPI background task docs?"
                ],
            },
        ],
    }
