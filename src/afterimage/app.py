from __future__ import annotations

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from afterimage import __version__
from afterimage.clock import SystemClock
from afterimage.discovery import agent_card, llms_txt, x402_well_known
from afterimage.facilitator import HttpFacilitator
from afterimage.fetch import HttpxFetcher
from afterimage.mcp import handle_rpc
from afterimage.models import Clock, Fetcher, SnapshotStore
from afterimage.pages import DEFAULT_MAX_AGE_S, PageResponse, fresh_snapshot, snapshot_page
from afterimage.pricing import SEARCH_ATOMIC, price_atomic
from afterimage.search import (
    DEFAULT_SEARCH_LIMIT,
    MAX_SEARCH_LIMIT,
    SearchResponse,
    search_corpus,
)
from afterimage.settings import Settings
from afterimage.store import SqliteSnapshotStore
from afterimage.x402 import Facilitator, require_payment, settlement_headers


def create_app(
    *,
    fetcher: Fetcher | None = None,
    store: SnapshotStore | None = None,
    clock: Clock | None = None,
    settings: Settings | None = None,
    facilitator: Facilitator | None = None,
) -> FastAPI:
    settings = settings or Settings()
    if fetcher is None:
        fetcher = HttpxFetcher()
    if store is None:
        store = SqliteSnapshotStore(settings.sqlite_path)
    if facilitator is None and settings.facilitator_url:
        facilitator = HttpFacilitator(settings.facilitator_url)
    app = FastAPI(
        title="AfterImage",
        version=__version__,
        description="Shared web snapshots for AI agents.",
    )
    app.state.fetcher = fetcher
    app.state.store = store
    app.state.clock = clock or SystemClock()
    app.state.settings = settings
    app.state.facilitator = facilitator

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "afterimage"}

    @app.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
    def get_llms_txt() -> str:
        return llms_txt(app.state.settings)

    @app.get("/.well-known/x402", include_in_schema=False)
    def get_x402() -> dict:
        return x402_well_known(app.state.settings)

    @app.get("/.well-known/agent-card.json", include_in_schema=False)
    def get_agent_card() -> dict:
        return agent_card(app.state.settings)

    @app.get(
        "/v1/page",
        response_model=None,
        responses={
            200: {"model": PageResponse, "description": "Readable snapshot"},
            400: {"description": "URL is not fetchable"},
            402: {"description": "x402 payment required"},
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
        response.headers.update(settlement_headers(payment))
        return response

    @app.get(
        "/v1/search",
        response_model=None,
        responses={
            200: {"model": SearchResponse, "description": "Corpus hits"},
            402: {"description": "x402 payment required"},
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
        response.headers.update(settlement_headers(payment))
        return response

    @app.post("/mcp", response_model=None)
    async def mcp_endpoint(message: dict) -> dict | Response:
        if app.state.fetcher is None or app.state.store is None:
            raise RuntimeError("AfterImage is not configured with a fetcher and store")
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

    return app


app = create_app()
