# AfterImage

**A shared copy of the public web for AI agents.**

If another agent already fetched a page, yours can reuse that copy (timestamp + sha256 hash) instead of scraping again. Search the copies. Humans buy credits on Stripe; agents send an API key.

Live (human landing): [https://afterimage.page](https://afterimage.page)  
Agent brief: [https://afterimage.page/llms.txt](https://afterimage.page/llms.txt)

## Get a key

```bash
curl -sS -X POST https://afterimage.page/v1/billing/checkout \
  -H 'content-type: application/json' \
  -d '{"pack":"starter"}'
```

Open `checkout_url`, pay **$5** (`starter`) or **$20** (`builder`). Save `api_key`. Do not publish it.

## Call it

Search stored pages (does **not** hit the live web, **$0.005**):

```bash
curl -sS 'https://afterimage.page/v1/search?q=fastapi+background+tasks' \
  -H "Authorization: Bearer ak_live_…"
```

Fetch or reuse one URL (**$0.002** if a fresh copy exists, **$0.01** if AfterImage has to download it):

```bash
curl -sS 'https://afterimage.page/v1/page?url=https://example.com/&max_age_s=900' \
  -H "Authorization: Bearer ak_live_…"
```

Check remaining dollars:

```bash
curl -sS https://afterimage.page/v1/billing/balance \
  -H "Authorization: Bearer ak_live_…"
```

HTTP **402** means missing key or empty credits — buy another pack.

## What you get back

**Search** — `indexed` (how many pages are stored), `hits[]` with `url`, `title`, `snippet`, `hash`, `fetched_at`. If `indexed` is 0, the library is empty; fetch some URLs first.

**Page** — `text` (readable extract, not HTML), `cache` (`hit` or `miss`), `hash` (sha256 of the raw body), `fetched_at`.

## Other endpoints

| Path | What it does |
|---|---|
| `GET /health` | Is the service up? |
| `GET /llms.txt` | Instructions for agents |
| `GET /openapi.json` | Full API spec |
| `POST /mcp` | Same search/fetch as JSON-RPC (`search_pages`, `get_page`). Needs the Bearer key or x402 on `tools/call`. |
| `GET /.well-known/mcp.json` | MCP server card (also `/mcp/server-card`) |
| `GET /.well-known/agent-card.json` | Agent card |
| `GET /.well-known/x402` | x402 USDC pay (live when `AFTERIMAGE_PAY_TO` is set) |

## Run a copy yourself

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
afterimage
pytest
```

Set `AFTERIMAGE_STRIPE_SECRET_KEY` and `AFTERIMAGE_STRIPE_WEBHOOK_SECRET` to charge. Webhook URL: `https://afterimage.page/v1/billing/webhook`, event `checkout.session.completed`. If a payment does not land on the key, open `/v1/billing/success?session_id=cs_live_…`.

## Limits

Caps: **5,000** pages, **32,000** characters per page, evicted after **10 days**. Error pages and status pages are not stored. Private/internal URLs are rejected. Oldest pages are dropped when the cap is hit. Live size: `GET /v1/stats` (free). Origin `robots.txt` is not honored today.

`scripts/seed.py` refills model catalogs, prices, versioned protocol specs, changelogs, and the FastAPI/Pydantic stack. GitHub Actions can run it Mondays if the repo secret `AFTERIMAGE_API_KEY` is a funded key. Weekly crawl, 10-day TTL, so a late or failed run does not empty the index.
