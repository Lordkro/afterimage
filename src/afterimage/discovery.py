from __future__ import annotations

from urllib.parse import urlparse

from afterimage import __version__
from afterimage.pricing import (
    HIT_USDC,
    MISS_ATOMIC,
    MISS_USDC,
    SEARCH_ATOMIC,
    SEARCH_USDC,
)
from afterimage.x402 import bazaar_extension
from afterimage.settings import USDC_EIP712_NAME, USDC_EIP712_VERSION, Settings

SERVER_CARD_SCHEMA = (
    "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"
)
MCP_REGISTRY_AUTH = (
    "v=MCPv1; k=ed25519; p=v+vVQvrK4Bau5XH7W1VApvWdFgNY3w9v75GyIQ6AgDU="
)
DESCRIPTION = (
    "Shared copies of public web pages for AI agents. Search stored pages or fetch a URL."
)


def reverse_dns_server_name(public_url: str, slug: str = "afterimage") -> str:
    host = (urlparse(public_url).hostname or "localhost").lower()
    if host in {"localhost", "127.0.0.1"}:
        return f"local.host/{slug}"
    return f"{'.'.join(reversed(host.split('.')))}/{slug}"


def mcp_server_card(settings: Settings) -> dict:
    base = settings.public_url.rstrip("/")
    return {
        "$schema": SERVER_CARD_SCHEMA,
        "name": reverse_dns_server_name(base),
        "title": "AfterImage",
        "description": DESCRIPTION,
        "version": __version__,
        "websiteUrl": base,
        "remotes": [{"type": "streamable-http", "url": f"{base}/mcp"}],
    }


def ai_catalog(settings: Settings) -> dict:
    base = settings.public_url.rstrip("/")
    host = urlparse(base).hostname or "localhost"
    return {
        "specVersion": "1.0",
        "entries": [
            {
                "identifier": f"urn:air:{host}:mcp:afterimage",
                "type": "application/mcp-server-card+json",
                "url": f"{base}/mcp/server-card",
            }
        ],
    }


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

HTTP 402 means unpaid. The JSON field code is one of:
- missing_key: no Authorization header (x402 clients pay here)
- unknown_key: bearer token is not a key from this instance
- unfunded_key: key was created but never paid for
- insufficient_credits: key is empty; buy another pack
GET {base}/v1/billing/balance with the same header to see remaining dollars.
Successful billed responses also send X-Credits-Remaining.

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
GET {base}/v1/stats is free and returns live indexed plus caps.
If indexed is 0, the library is empty. Fetch URLs with /v1/page, then search again.
If hits is empty but indexed > 0, nothing matched. Try different words or fetch the URL.

## 3. Fetch or reuse a URL

GET {base}/v1/page?url=https://example.com/pricing&max_age_s=900

Live fetches always send this fixed header set (never Cookie, never Authorization):
  User-Agent: AfterImage/0.1 (+https://github.com/Lordkro/afterimage; agent-snapshot)
  Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
  Accept-Language: en-US,en;q=0.9
The stored copy is that one variant. If the origin sent Vary, it is returned as
vary. Locale- or UA-specific pages may not match a different client.

Query:
- url (required): http or https. No logins, no private/internal addresses.
- max_age_s (optional, default 900): reuse a stored copy if it is no older than this

Response:
- cache: "hit" (reused) or "miss" (live fetch)
- text: readable extract, not HTML
- hash: sha256 of the raw response body
- fetched_at, age_s, status, title, final_url
- truncated: true if text hit the character cap
- stored: false if AfterImage did not keep a copy
- stored_reason: noarchive | vary | http_error | thin_extract | volatile | challenge
- origin_max_age_s: remaining origin freshness in seconds (s-maxage/max-age
  minus Age, or Expires; 0 for no-cache / no-store / private). Reuse is min(your max_age_s,
  origin_max_age_s, {settings.snapshot_ttl_days}-day TTL).
- vary, etag, last_modified: origin validators when present (etag/last-modified
  are stored for later revalidation; they do not change price today)

Reuse of a stored copy is min(your max_age_s, origin_max_age_s, {settings.snapshot_ttl_days}-day TTL).
If you already have the URL from a search hit, call /v1/page to get the full text.
If cache=hit, do not fetch the origin yourself unless you need a smaller max_age_s.

## MCP

POST {base}/mcp
JSON-RPC. Tools: search_pages, get_page.
initialize and tools/list are free. tools/call for those two tools needs the same
Authorization header as HTTP, or x402 USDC. HTTP 402 if unpaid.

Server card: GET {base}/.well-known/mcp.json
Also: GET {base}/mcp/server-card

## Other

- Health: GET {base}/health (includes live indexed)
- Stats: GET {base}/v1/stats (free; indexed and caps)
- OpenAPI: GET {base}/openapi.json
- Agent card: GET {base}/.well-known/agent-card.json
- x402 discovery: GET {base}/.well-known/x402
- robots.txt: GET {base}/robots.txt

## Policy

AfterImage caches public http(s) pages for agents. It rejects private/internal
addresses and does not follow logins. It does not currently honor origin
robots.txt crawl rules.
Live fetch honors noarchive (meta robots and X-Robots-Tag) and Vary: *:
the caller still gets the page; AfterImage does not store it.
Cache-Control no-store / private / no-cache is stored for search (AfterImage
is a snapshot index, not a shared HTTP cache) but origin freshness is 0, so
/v1/page always refetches those URLs and bills at the live-fetch rate.
Age is subtracted from max-age.
stored_reason is why a live fetch was not kept:
- noarchive / vary: the origin asked not to archive, or Vary: *
- volatile: AfterImage will not index status pages (stale "up" is worse than a miss)
- challenge: bot interstitial (Cloudflare and similar)
- thin_extract / http_error: extract was a JS shell, title-only, fat HTML with
  almost no body, an order of magnitude shorter than the copy already stored,
  or an HTTP error
noarchive, Vary: *, and volatile delete any stored copy. challenge and
thin_extract leave the previous copy in place so a wall does not replace a
working snapshot.
Copies that are stored are evicted after {settings.snapshot_ttl_days} days or when the 5,000-page cap
drops the oldest. Caps and live size: GET {base}/v1/stats.
To request removal of a stored URL, email {settings.removal_email}.
"""


def x402_well_known(settings: Settings) -> dict:
    base = settings.public_url.rstrip("/")
    resource_url = f"{base}/v1/page"
    pay_to = settings.pay_to.strip()
    extra = {"name": USDC_EIP712_NAME, "version": USDC_EIP712_VERSION}

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
        "description": (
            "Shared copies of public web pages for AI agents. Search first, then fetch. "
            "Pay with a Stripe API key or x402 USDC on Base."
        ),
        "resources": [
            {
                "url": resource_url,
                "description": (
                    f"GET /v1/page. Reuse a stored copy (${HIT_USDC}) or fetch live (${MISS_USDC})."
                ),
                "mimeType": "application/json",
                "accepts": [accept(MISS_ATOMIC)] if pay_to else [],
                "extensions": bazaar_extension("/v1/page"),
            },
            {
                "url": f"{base}/v1/search",
                "description": (
                    f"GET /v1/search. Search stored copies only. ${SEARCH_USDC}. "
                    "Does not visit the live web."
                ),
                "mimeType": "application/json",
                "accepts": [accept(SEARCH_ATOMIC)] if pay_to else [],
                "extensions": bazaar_extension("/v1/search"),
            },
            {
                "url": f"{base}/mcp",
                "description": "MCP tools search_pages and get_page over streamable HTTP.",
                "mimeType": "application/json",
                "accepts": [accept(MISS_ATOMIC)] if pay_to else [],
                "extensions": bazaar_extension("/mcp", tool_name="get_page"),
            },
        ],
    }


def agent_card(settings: Settings) -> dict:
    base = settings.public_url.rstrip("/")
    return {
        "name": "AfterImage",
        "description": (
            DESCRIPTION
            + " Paid: Authorization Bearer ak_live_… or x402. HTTP 402 if unpaid."
        ),
        "url": base,
        "version": __version__,
        "protocolVersion": "0.3.0",
        "capabilities": {"streaming": False},
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["application/json"],
        "securitySchemes": {
            "bearer": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "Bearer ak_live_… from POST /v1/billing/checkout, or x402 PAYMENT-SIGNATURE.",
            }
        },
        "security": [{"bearer": []}],
        "skills": [
            {
                "id": "get_page",
                "name": "Get page snapshot",
                "description": (
                    "Paid. Return readable text for a public http(s) URL. Reuses a stored copy "
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
                    "Paid. Search pages already stored in AfterImage. Does not scrape the live web. "
                    "Use get_page for the full text of a hit."
                ),
                "tags": ["search", "web", "cache"],
                "examples": [
                    "Search stored pages for FastAPI background tasks"
                ],
            },
        ],
    }
