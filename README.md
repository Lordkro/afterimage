# AfterImage

Shared web snapshots for AI agents. Fetch a page once, reuse it with provenance instead of scraping it again.

```http
GET /v1/search?q=fastapi+background+tasks
GET /v1/page?url=https://example.com/pricing&max_age_s=900
```

Search only ranks pages AfterImage has already fetched — it never hits the live web.  
Miss (live fetch): priced as a fetch.  
Hit (fresh enough): priced as a reuse. Same bytes, same hash, `cache: "hit"`.

## Why

Internet agents spend most of their paid calls looking at the same URLs. AfterImage is the afterimage of those looks: a snapshot with `fetched_at`, a content hash, and readable text an agent can trust without re-fetching.

## Agent entrypoints

| Path | What it is |
|---|---|
| `GET /v1/search` | Search the fetched corpus (no live fetch) |
| `GET /v1/page` | Snapshot a URL |
| `GET /health` | Liveness |
| `GET /llms.txt` | Machine-readable product brief |
| `GET /openapi.json` | OpenAPI 3 |
| `GET /.well-known/x402` | x402 v2 discovery |
| `GET /.well-known/agent-card.json` | A2A agent card |
| `POST /mcp` | MCP JSON-RPC (`search_pages`, `get_page`) |

Humans buy credits with Stripe (`POST /v1/billing/checkout`). Agents send `Authorization: Bearer ak_live_…`. Per-call card charges are not used — Stripe's fees would eat a $0.002 hit. x402 USDC remains optional if `AFTERIMAGE_PAY_TO` is set.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
afterimage
# or: uvicorn afterimage.app:app --reload
```

```bash
pytest
```

## Snapshot shape

```json
{
  "url": "https://example.com/pricing",
  "final_url": "https://example.com/pricing",
  "status": 200,
  "title": "Pricing",
  "text": "…readable extract…",
  "hash": "sha256:…",
  "fetched_at": "2026-08-27T18:41:02Z",
  "age_s": 0,
  "cache": "miss",
  "price_usdc": "0.01"
}
```

`hash` is SHA-256 of the raw response body. `text` is a readable extract, not a raw HTML dump.

## Search shape

```json
{
  "q": "Pro is $9",
  "indexed": 1,
  "hits": [
    {
      "url": "https://example.com/pricing",
      "title": "Pricing",
      "snippet": "Pro is $9 per month.",
      "hash": "sha256:…",
      "fetched_at": "2026-08-27T18:41:02Z",
      "age_s": 60,
      "status": 200,
      "score": 4.5
    }
  ],
  "price_usdc": "0.005"
}
```

If `indexed` is 0, nobody has fetched yet — call `/v1/page` first. Title matches rank above body-only matches.

## Safety

AfterImage refuses to fetch loopback, link-local, and private addresses. Redirects are re-checked. This is a public fetch API; SSRF is part of the product, not a later patch.

## Storage caps

This is a cache, not an archive. Defaults keep a Railway volume small:

| Cap | Default | Env |
|---|---|---|
| Snapshots kept | 5,000 | `AFTERIMAGE_MAX_SNAPSHOTS` |
| Text per page | 32,000 chars | `AFTERIMAGE_MAX_TEXT_CHARS` |
| Snapshot TTL | 7 days | `AFTERIMAGE_SNAPSHOT_TTL_S` |
| Error pages | not stored | `AFTERIMAGE_PERSIST_ERROR_PAGES` |

Raw HTML is never stored — only the readable extract. When the corpus is full, the oldest snapshots are dropped.
