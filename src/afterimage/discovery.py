from __future__ import annotations

from afterimage import __version__
from afterimage.pricing import (
    HIT_ATOMIC,
    HIT_USDC,
    MISS_ATOMIC,
    MISS_USDC,
    SEARCH_ATOMIC,
    SEARCH_USDC,
)
from afterimage.settings import Settings


def llms_txt(settings: Settings) -> str:
    base = settings.public_url.rstrip("/")
    return f"""# AfterImage

AfterImage is a shared copy of the public web for AI agents.
If a page was fetched recently, reuse that copy instead of scraping again.
Each copy has a timestamp and a sha256 hash of the raw bytes.

Base URL: {base}
Do not scrape this file. Call the JSON endpoints below.

## 1. Get a key (human, once)

POST {base}/v1/billing/checkout
Content-Type: application/json

{{"pack":"starter"}}

Packs: starter = $5 USD, builder = $20 USD.
The JSON returns api_key and checkout_url.
Open checkout_url, pay, then keep api_key secret.
Send it on every later request:

  Authorization: Bearer ak_live_…

HTTP 402 means the header is missing or the key has no credits left. Buy another pack.
GET {base}/v1/billing/balance with the same header to see remaining dollars.

Prices:
- GET /v1/search = ${SEARCH_USDC} per call
- GET /v1/page cache hit = ${HIT_USDC} (copy still fresh)
- GET /v1/page live fetch = ${MISS_USDC} (origin was contacted)

Optional: x402 USDC on Base instead of a key, if this instance advertises it
at GET {base}/.well-known/x402

## 2. Search copies (does not visit the live web)

GET {base}/v1/search?q=fastapi+background+tasks

Query:
- q (required): words to find in titles and text
- limit (optional, default 10, max 50)
- max_age_s (optional): only copies this many seconds old

Response:
- indexed: how many copies are stored
- hits[]: url, title, snippet, hash, fetched_at, age_s, status, score
If indexed is 0, the library is empty. Fetch URLs with /v1/page, then search again.
If hits is empty but indexed > 0, nothing matched. Try different words or fetch the URL.

## 3. Fetch or reuse a URL

GET {base}/v1/page?url=https://example.com/pricing&max_age_s=900

Query:
- url (required): http or https. No logins, no private/internal addresses.
- max_age_s (optional, default 900): reuse a stored copy if it is no older than this

Response:
- cache: "hit" (reused) or "miss" (live fetch)
- text: readable extract, not HTML
- hash: sha256 of the raw response body
- fetched_at, age_s, status, title, final_url

If you already have the URL from a search hit, call /v1/page to get the full text.
If cache=hit, do not fetch the origin yourself unless you need a smaller max_age_s.

## MCP

POST {base}/mcp
JSON-RPC. Tools: search_pages, get_page.
initialize and tools/list are free. tools/call for those two tools needs the same
Authorization header as HTTP. HTTP 402 if unpaid.

## Other

- Health: GET {base}/health
- OpenAPI: GET {base}/openapi.json
- Agent card: GET {base}/.well-known/agent-card.json
- x402 discovery: GET {base}/.well-known/x402
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
        "serviceName": "AfterImage",
        "description": "Shared copies of public web pages for AI agents. Search first, then fetch.",
        "resources": [
            {
                "url": resource_url,
                "description": (
                    f"GET /v1/page. Reuse a stored copy (${HIT_USDC}) or fetch live (${MISS_USDC})."
                ),
                "mimeType": "application/json",
                "accepts": [accept(HIT_ATOMIC), accept(MISS_ATOMIC)],
            },
            {
                "url": f"{base}/v1/search",
                "description": (
                    f"GET /v1/search. Search stored copies only. ${SEARCH_USDC}. "
                    "Does not visit the live web."
                ),
                "mimeType": "application/json",
                "accepts": [accept(SEARCH_ATOMIC)],
            },
        ],
    }


def agent_card(settings: Settings) -> dict:
    base = settings.public_url.rstrip("/")
    return {
        "name": "AfterImage",
        "description": (
            "Shared copies of public web pages for AI agents. "
            "Search stored pages, or fetch a URL to add/reuse a copy with a timestamp and hash."
        ),
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
                    "Return readable text for a public http(s) URL. Reuses a stored copy "
                    "if it is newer than max_age_s. Includes sha256 hash and fetched_at."
                ),
                "tags": ["web", "cache", "search", "http"],
                "examples": [
                    "Get https://fastapi.tiangolo.com/tutorial/background-tasks/ if it is under 15 minutes old"
                ],
            },
            {
                "id": "search_pages",
                "name": "Search fetched pages",
                "description": (
                    "Search pages already stored in AfterImage. Does not scrape the live web. "
                    "Use get_page for the full text of a hit."
                ),
                "tags": ["search", "web", "cache"],
                "examples": [
                    "Search stored pages for FastAPI background tasks"
                ],
            },
        ],
    }
