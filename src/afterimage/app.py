from __future__ import annotations

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

from afterimage import __version__
from afterimage.checkout import (
    Checkout,
    CheckoutRequest,
    StripeCheckout,
    _get,
    apply_paid_session,
)
from afterimage.clock import SystemClock
from afterimage.discovery import (
    MCP_REGISTRY_AUTH,
    agent_card,
    ai_catalog,
    llms_txt,
    mcp_server_card,
    x402_well_known,
)
from afterimage.landing import landing_html
from afterimage.facilitator import HttpFacilitator
from afterimage.fetch import HttpxFetcher
from afterimage.keys import KeyStore, SqliteKeyStore
from afterimage.mcp import handle_rpc
from afterimage.models import Clock, Fetcher, SnapshotStore
from afterimage.packs import PACKS, get_pack
from afterimage.pages import DEFAULT_MAX_AGE_S, PageResponse, fresh_snapshot, snapshot_page
from afterimage.pricing import SEARCH_ATOMIC, price_atomic
from afterimage.search import (
    DEFAULT_SEARCH_LIMIT,
    MAX_SEARCH_LIMIT,
    SearchResponse,
    search_corpus,
)
from afterimage.settings import Settings, paid_mode
from afterimage.store import SqliteSnapshotStore
from afterimage.rate_limit import SlidingWindow
from afterimage.x402 import Facilitator, billed_headers, require_payment, unpaid_response


def create_app(
    *,
    fetcher: Fetcher | None = None,
    store: SnapshotStore | None = None,
    clock: Clock | None = None,
    settings: Settings | None = None,
    facilitator: Facilitator | None = None,
    keys: KeyStore | None = None,
    checkout: Checkout | None = None,
) -> FastAPI:
    settings = settings or Settings()
    if fetcher is None:
        fetcher = HttpxFetcher()
    if store is None:
        store = SqliteSnapshotStore(settings.sqlite_path)
    if facilitator is None and settings.facilitator_url:
        facilitator = HttpFacilitator(settings.facilitator_url)
    if keys is None and settings.stripe_secret_key:
        keys = SqliteKeyStore(settings.sqlite_path)
    if checkout is None and settings.stripe_secret_key:
        checkout = StripeCheckout(
            secret_key=settings.stripe_secret_key,
            public_url=settings.public_url,
        )
    app = FastAPI(
        title="AfterImage",
        version=__version__,
        description=(
            "Shared copies of public web pages for AI agents. "
            "Send Authorization: Bearer ak_live_… or pay with x402. HTTP 402 if unpaid."
        ),
    )
    app.state.fetcher = fetcher
    app.state.store = store
    app.state.clock = clock or SystemClock()
    app.state.settings = settings
    app.state.facilitator = facilitator
    app.state.keys = keys
    app.state.checkout = checkout
    app.state.checkout_limit = SlidingWindow(max_hits=10, window_s=600)

    @app.exception_handler(RequestValidationError)
    async def challenge_before_invalid_query(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        path = request.url.path
        if paid_mode(app.state.settings) and path in {"/v1/page", "/v1/search"}:
            amount = (
                SEARCH_ATOMIC
                if path.endswith("/v1/search")
                else price_atomic(cache_hit=False)
            )
            return unpaid_response(
                settings=app.state.settings,
                resource_path=path,
                amount=amount,
                description=(
                    "Search already-fetched web snapshots"
                    if path.endswith("/v1/search")
                    else "Reusable web snapshot with provenance"
                ),
                error="Payment required. Buy credits via Stripe checkout or pay with x402.",
            )
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    async def _stats() -> dict:
        indexed = 0
        if app.state.store is not None:
            indexed = await app.state.store.count()
        return {
            "indexed": indexed,
            "max_snapshots": app.state.settings.max_snapshots,
            "max_text_chars": app.state.settings.max_text_chars,
            "snapshot_ttl_s": app.state.settings.snapshot_ttl_s,
        }

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def home() -> str:
        return landing_html(app.state.settings)

    @app.get("/health")
    async def health() -> dict:
        stats = await _stats()
        return {"status": "ok", "service": "afterimage", **stats}

    @app.get("/v1/stats")
    async def stats() -> dict:
        return await _stats()

    @app.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
    def get_llms_txt() -> str:
        return llms_txt(app.state.settings)

    def _public_json(
        content: dict,
        *,
        media_type: str = "application/json",
        cache: str = "public, max-age=3600",
    ) -> JSONResponse:
        return JSONResponse(
            content,
            media_type=media_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "Content-Type, If-None-Match",
                "Cache-Control": cache,
            },
        )

    @app.get("/.well-known/x402", include_in_schema=False)
    def get_x402() -> JSONResponse:
        return _public_json(
            x402_well_known(app.state.settings),
            cache="no-store",
        )

    @app.get("/.well-known/agent-card.json", include_in_schema=False)
    def get_agent_card() -> JSONResponse:
        return _public_json(agent_card(app.state.settings))

    @app.get("/.well-known/mcp.json", include_in_schema=False)
    def get_mcp_json() -> JSONResponse:
        return _public_json(mcp_server_card(app.state.settings))

    @app.get("/.well-known/mcp/server-card.json", include_in_schema=False)
    def get_mcp_server_card_well_known() -> JSONResponse:
        return _public_json(
            mcp_server_card(app.state.settings),
            media_type="application/mcp-server-card+json",
        )

    @app.get("/mcp/server-card", include_in_schema=False)
    def get_mcp_server_card() -> JSONResponse:
        return _public_json(
            mcp_server_card(app.state.settings),
            media_type="application/mcp-server-card+json",
        )

    @app.get("/.well-known/ai-catalog.json", include_in_schema=False)
    def get_ai_catalog() -> JSONResponse:
        return _public_json(
            ai_catalog(app.state.settings),
            media_type="application/ai-catalog+json",
        )

    @app.get(
        "/.well-known/mcp-registry-auth",
        response_class=PlainTextResponse,
        include_in_schema=False,
    )
    def get_mcp_registry_auth() -> str:
        return MCP_REGISTRY_AUTH

    @app.get(
        "/v1/page",
        response_model=None,
        responses={
            200: {"model": PageResponse, "description": "Readable snapshot"},
            400: {"description": "URL is not fetchable"},
            402: {"description": "Payment required (API key or x402)"},
        },
    )
    async def get_page(
        request: Request,
        url: str = Query(..., description="http(s) URL to snapshot"),
        max_age_s: int = Query(
            DEFAULT_MAX_AGE_S,
            ge=0,
            description="Reuse a cached snapshot if it is no older than this many seconds.",
        ),
    ) -> PageResponse | JSONResponse:
        if app.state.fetcher is None or app.state.store is None:
            raise RuntimeError("AfterImage is not configured with a fetcher and store")
        cached = await fresh_snapshot(
            url,
            max_age_s=max_age_s,
            store=app.state.store,
            clock=app.state.clock,
        )
        payment = await require_payment(
            request,
            settings=app.state.settings,
            facilitator=app.state.facilitator,
            amount=price_atomic(cache_hit=cached is not None),
            resource_path="/v1/page",
            keys=app.state.keys,
        )
        if isinstance(payment, JSONResponse):
            return payment
        page = await snapshot_page(
            url,
            max_age_s=max_age_s,
            store=app.state.store,
            fetcher=app.state.fetcher,
            clock=app.state.clock,
            settings=app.state.settings,
        )
        if payment is None:
            return page
        response = JSONResponse(page.model_dump())
        response.headers.update(billed_headers(payment))
        return response

    @app.get(
        "/v1/search",
        response_model=None,
        responses={
            200: {"model": SearchResponse, "description": "Corpus hits"},
            402: {"description": "Payment required (API key or x402)"},
            422: {"description": "Query is empty"},
        },
    )
    async def search_pages(
        request: Request,
        q: str = Query(..., description="Search the already-fetched corpus. Does not hit the live web."),
        limit: int = Query(DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT),
        max_age_s: int | None = Query(
            None,
            ge=0,
            description="Only return snapshots no older than this many seconds.",
        ),
    ) -> SearchResponse | JSONResponse:
        if app.state.store is None:
            raise RuntimeError("AfterImage is not configured with a store")
        payment = await require_payment(
            request,
            settings=app.state.settings,
            facilitator=app.state.facilitator,
            amount=SEARCH_ATOMIC,
            resource_path="/v1/search",
            description="Search already-fetched web snapshots",
            keys=app.state.keys,
        )
        if isinstance(payment, JSONResponse):
            return payment
        result = await search_corpus(
            q,
            store=app.state.store,
            clock=app.state.clock,
            limit=limit,
            max_age_s=max_age_s,
            settings=app.state.settings,
        )
        if payment is None:
            return result
        response = JSONResponse(result.model_dump())
        response.headers.update(billed_headers(payment))
        return response

    @app.post(
        "/mcp",
        response_model=None,
        responses={402: {"description": "Payment required (API key or x402)"}},
    )
    async def mcp_endpoint(request: Request, message: dict) -> dict | Response:
        if app.state.fetcher is None or app.state.store is None:
            raise RuntimeError("AfterImage is not configured with a fetcher and store")
        if message.get("method") == "tools/call":
            params = message.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            amount = None
            if name == "search_pages":
                amount = SEARCH_ATOMIC
            elif name == "get_page":
                page_url = arguments.get("url")
                if page_url:
                    try:
                        cached = await fresh_snapshot(
                            page_url,
                            max_age_s=int(
                                arguments.get("max_age_s", DEFAULT_MAX_AGE_S)
                            ),
                            store=app.state.store,
                            clock=app.state.clock,
                        )
                        amount = price_atomic(cache_hit=cached is not None)
                    except Exception:
                        amount = None
            if amount is not None:
                payment = await require_payment(
                    request,
                    settings=app.state.settings,
                    facilitator=app.state.facilitator,
                    amount=amount,
                    resource_path="/mcp",
                    keys=app.state.keys,
                    tool_name=name,
                )
                if isinstance(payment, JSONResponse):
                    return payment
        reply = await handle_rpc(
            message,
            store=app.state.store,
            fetcher=app.state.fetcher,
            clock=app.state.clock,
            settings=app.state.settings,
        )
        if reply is None:
            return Response(status_code=204)
        return reply

    @app.post("/v1/billing/checkout")
    async def billing_checkout(
        request: Request, body: CheckoutRequest = CheckoutRequest()
    ) -> JSONResponse:
        if app.state.keys is None or app.state.checkout is None:
            return JSONResponse(
                status_code=503, content={"error": "Stripe billing is not configured"}
            )
        ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        if not ip and request.client:
            ip = request.client.host
        if ip and not app.state.checkout_limit.allow(ip):
            return JSONResponse(
                status_code=429, content={"error": "checkout rate limit"}
            )
        pack = get_pack(body.pack or "starter")
        if pack is None:
            return JSONResponse(
                status_code=422,
                content={"error": "unknown pack", "packs": list(PACKS)},
            )
        key_id, secret = await app.state.keys.issue()
        checkout_url = await app.state.checkout.create_session(
            key_id=key_id, pack=pack.id, cents=pack.cents
        )
        return JSONResponse(
            {
                "api_key": secret,
                "key_id": key_id,
                "checkout_url": checkout_url,
                "pack": pack.id,
                "credits_usd": pack.micros / 1_000_000,
            }
        )

    @app.get("/v1/billing/balance")
    async def billing_balance(request: Request) -> JSONResponse:
        if app.state.keys is None:
            return JSONResponse(status_code=503, content={"error": "billing off"})
        from afterimage.x402 import _bearer_secret

        secret = _bearer_secret(request)
        if not secret:
            return JSONResponse(status_code=401, content={"error": "missing API key"})
        micros = await app.state.keys.balance(secret)
        if micros is None:
            return JSONResponse(status_code=401, content={"error": "unknown API key"})
        return JSONResponse({"credits_usd": micros / 1_000_000, "micros": micros})

    async def _fulfill(session_id: str) -> JSONResponse:
        if app.state.keys is None or app.state.checkout is None:
            return JSONResponse(status_code=503, content={"error": "billing off"})
        try:
            session = await app.state.checkout.retrieve_session(session_id)
        except Exception:
            return JSONResponse(status_code=404, content={"error": "unknown session"})
        result = await apply_paid_session(app.state.keys, session)
        status = 200 if result.get("credited") else 402
        return JSONResponse(result, status_code=status)

    @app.post("/v1/billing/webhook", include_in_schema=False)
    async def billing_webhook(request: Request) -> JSONResponse:
        if not app.state.settings.stripe_webhook_secret:
            return JSONResponse(status_code=503, content={"error": "webhook not configured"})
        import stripe

        payload = await request.body()
        sig = request.headers.get("stripe-signature", "")
        try:
            event = stripe.Webhook.construct_event(
                payload, sig, app.state.settings.stripe_webhook_secret
            )
        except Exception:
            return JSONResponse(status_code=400, content={"error": "invalid signature"})
        event_type = _get(event, "type")
        if event_type == "checkout.session.completed":
            data = _get(_get(event, "data"), "object")
            session_id = str(_get(data, "id") or "")
            if session_id:
                return await _fulfill(session_id)
        return JSONResponse({"ok": True})

    @app.get("/v1/billing/success", include_in_schema=False)
    async def billing_success(session_id: str | None = None) -> JSONResponse:
        if not session_id:
            return JSONResponse({"error": "session_id required"}, status_code=422)
        return await _fulfill(session_id)

    @app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
    def robots() -> str:
        base = app.state.settings.public_url.rstrip("/")
        return (
            "# AfterImage caches public pages for AI agents. See /llms.txt Policy.\n"
            "User-agent: *\n"
            "Allow: /\n"
            f"Allow: /llms.txt\n"
            f"# Live corpus size: {base}/v1/stats\n"
        )

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        from fastapi.openapi.utils import get_openapi

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schema.setdefault("components", {})["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "API key",
                "description": "ak_live_… from POST /v1/billing/checkout. HTTP 402 if missing or empty. x402 PAYMENT-SIGNATURE is an alternative.",
            }
        }
        for path in ("/v1/page", "/v1/search", "/v1/billing/balance", "/mcp"):
            item = schema.get("paths", {}).get(path) or {}
            for op in item.values():
                if isinstance(op, dict):
                    op.setdefault("security", [{"BearerAuth": []}])
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
    return app


app = create_app()
