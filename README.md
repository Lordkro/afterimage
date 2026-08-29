# AfterImage

**Fresh copies of the pages models get wrong.**

Model catalogs, provider prices, dated protocol specs, changelogs, deprecations, rate limits, current package versions. If another agent already fetched a page, yours reuses that copy — timestamp plus sha256 of the raw bytes.

Humans buy credits on Stripe; agents send `Authorization: Bearer ak_live_…`. Or pay per call with x402 USDC on Base.

Live: [afterimage.page](https://afterimage.page)  
Docs: [afterimage.page/docs](https://afterimage.page/docs)  
Agent brief: [afterimage.page/llms.txt](https://afterimage.page/llms.txt)  
MCP: `POST https://afterimage.page/mcp`

## Buy a key

You get the API key **before** Stripe — save it, then pay. Same key for HTTP, MCP, and balance.

```bash
curl -sS -X POST https://afterimage.page/v1/billing/checkout \
  -H 'content-type: application/json' \
  -d '{"pack":"starter"}'
```

Open `checkout_url`. Packs:

| Pack | Price | Roughly |
|---|---|---|
| `starter` | **$5** | 1,000 searches, or 500 live fetches, or 2,500 cache hits |
| `builder` | **$20** | 4,000 searches, or 2,000 live fetches, or 10,000 cache hits |

Do not publish the key. HTTP **402** is unpaid. `code` is one of `missing_key`, `unknown_key`, `unfunded_key`, `insufficient_credits`.

x402 clients skip the key: unpaid calls return 402 with payment terms. Production settles USDC on Base (`eip155:8453`) via [PayAI](https://facilitator.payai.network). Discovery: [GET /.well-known/x402](https://afterimage.page/.well-known/x402).

## Call it

Search stored pages (does **not** hit the live web, **$0.005**):

```bash
curl -sS 'https://afterimage.page/v1/search?q=openai+pricing' \
  -H "Authorization: Bearer ak_live_…"
```

Fetch or reuse one URL (**$0.002** if a fresh copy exists, **$0.01** if AfterImage has to download it):

```bash
curl -sS 'https://afterimage.page/v1/page?url=https://platform.openai.com/docs/pricing&max_age_s=900' \
  -H "Authorization: Bearer ak_live_…"
```

Remaining dollars:

```bash
curl -sS https://afterimage.page/v1/billing/balance \
  -H "Authorization: Bearer ak_live_…"
```

Billed responses also send `X-Credits-Remaining`. Live library size is free: [GET /v1/stats](https://afterimage.page/v1/stats).

## What you get back

**Search** — `indexed`, `hits[]` with `url`, `title`, `snippet`, `hash`, `fetched_at`, `age_s`, `status`, `score`, `truncated`, `aliases` (other URLs with the same hash). If `indexed` is 0, the library is empty; fetch a URL first. If `hits` is empty but `indexed` > 0, nothing matched.

**Page** — readable `text` (not HTML), `cache` (`hit` or `miss`), `hash` (sha256 of the raw body), `fetched_at`, `stored`, `stored_reason`. Reuse is `min(your max_age_s, origin_max_age_s, 10-day TTL)`. Default `max_age_s` is 900.

## MCP

JSON-RPC at `POST https://afterimage.page/mcp`. Tools: `search_pages`, `get_page`. `initialize` and `tools/list` are free; `tools/call` needs the Bearer key or x402.

```bash
curl -sS -X POST https://afterimage.page/mcp \
  -H "Authorization: Bearer ak_live_…" \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search_pages","arguments":{"q":"openai pricing"}}}'
```

Server card: [/.well-known/mcp.json](https://afterimage.page/.well-known/mcp.json) (also `/mcp/server-card`). Remote name is `page.afterimage/afterimage`.

## Other endpoints

| Path | What it does |
|---|---|
| `GET /` | Human landing |
| `GET /docs` | Human docs + OpenAPI UI |
| `GET /health` | Up, plus live indexed |
| `GET /v1/stats` | Indexed count and caps (free) |
| `GET /v1/gaps` | Zero-hit search queries (crawl list from real misses) |
| `GET /llms.txt` | Instructions for agents |
| `GET /openapi.json` | Full API spec |
| `POST /v1/billing/checkout` | Stripe pack → `api_key` + `checkout_url` |
| `GET /v1/billing/balance` | Remaining credits |
| `POST /v1/billing/webhook` | Stripe `checkout.session.completed` |
| `GET /v1/billing/success` | Credit a paid session if the webhook missed |
| `GET /.well-known/x402` | x402 resources (search, page, both MCP tools) |
| `GET /.well-known/agent-card.json` | Agent card |
| `GET /.well-known/ai-catalog.json` | MCP catalog pointer |
| `GET /robots.txt` | Crawl rules for AfterImage itself |

## Limits

AfterImage is a **cache, not an archive**. Caps: **5,000** pages, **100,000** characters per page, evicted after **10 days**. Oldest pages drop when the cap is hit. Private/internal URLs are rejected. Live fetches send a fixed User-Agent (`AfterImage/0.1 (+https://github.com/Lordkro/afterimage; agent-snapshot)`); never Cookie, never Authorization.

Not stored: HTTP errors, status pages, `noarchive`, `Vary: *`. Origin `Cache-Control: no-store` / `private` / `no-cache` is indexed for search but never reused as a cache hit (billed at the live-fetch rate). Stdlib, PEPs, MDN, RFCs, and similar training-data hosts are fetchable, not sold. Origin `robots.txt` is not honored today. Removal: [removal@afterimage.page](mailto:removal@afterimage.page).

## Seed

`scripts/seed_urls.txt` is the moving class: provider prices and model lists, versioned MCP/OpenAPI/x402 specs, changelogs, deprecations, rate limits, infra pricing, current PyPI metadata. Status pages are not listed. GitHub Actions runs `scripts/seed.py` Mondays (and on demand) if repo secret `AFTERIMAGE_API_KEY` is a funded key. Weekly crawl, 10-day TTL, so a late run does not empty the index. The log prints `chars=` and `stored_reason` per URL; a 10× drop is a challenge page or an empty shell.

`scripts/x402_ping.py` pays once each for `/v1/search`, `/v1/page`, and both MCP tools so PayAI can catalog them.

## Run a copy yourself

Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
afterimage
pytest
```

Env vars are `AFTERIMAGE_*` (see `.env.example`). Stripe: `AFTERIMAGE_STRIPE_SECRET_KEY` and `AFTERIMAGE_STRIPE_WEBHOOK_SECRET`. Webhook URL: `https://afterimage.page/v1/billing/webhook`, event `checkout.session.completed`. If a payment does not land on the key, open `/v1/billing/success?session_id=cs_live_…`. x402: set `AFTERIMAGE_PAY_TO` to a Base address; facilitator defaults to PayAI.

Docker: `Dockerfile` listens on 8080 and stores SQLite at `/data/afterimage.db`.
