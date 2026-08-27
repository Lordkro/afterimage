from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from already.extract import extract_readable
from already.hashing import sha256_bytes
from already.models import Clock, Fetcher, Snapshot, SnapshotStore
from already.pricing import price_usdc
from already.urls import require_public_http_url

DEFAULT_MAX_AGE_S = 900


class PageResponse(BaseModel):
    url: str
    final_url: str
    status: int
    title: str
    text: str
    hash: str
    fetched_at: str
    age_s: int
    cache: str
    price_usdc: str
    max_age_s: int = Field(default=DEFAULT_MAX_AGE_S)


def iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


async def fresh_snapshot(
    url: str,
    *,
    max_age_s: int,
    store: SnapshotStore,
    clock: Clock,
) -> Snapshot | None:
    url = require_public_http_url(url)
    existing = await store.get(url)
    if existing is None:
        return None
    age_s = int((clock.now() - existing.fetched_at).total_seconds())
    if age_s <= max_age_s:
        return existing
    return None


async def snapshot_page(
    url: str,
    *,
    max_age_s: int,
    store: SnapshotStore,
    fetcher: Fetcher,
    clock: Clock,
) -> PageResponse:
    url = require_public_http_url(url)
    if max_age_s < 0:
        max_age_s = 0
    now = clock.now()
    existing = await fresh_snapshot(
        url, max_age_s=max_age_s, store=store, clock=clock
    )
    if existing is not None:
        return _view(existing, now=now, cache="hit", max_age_s=max_age_s)

    fetched = await fetcher.fetch(url)
    title, text = extract_readable(fetched.body, fetched.content_type)
    snapshot = Snapshot(
        url=url,
        final_url=fetched.final_url,
        status=fetched.status,
        title=title,
        text=text,
        content_hash=sha256_bytes(fetched.body),
        fetched_at=now,
        content_type=fetched.content_type,
    )
    await store.put(snapshot)
    return _view(snapshot, now=now, cache="miss", max_age_s=max_age_s)


def _view(
    snapshot: Snapshot, *, now: datetime, cache: str, max_age_s: int
) -> PageResponse:
    age_s = max(0, int((now - snapshot.fetched_at).total_seconds()))
    return PageResponse(
        url=snapshot.url,
        final_url=snapshot.final_url,
        status=snapshot.status,
        title=snapshot.title,
        text=snapshot.text,
        hash=snapshot.content_hash,
        fetched_at=iso_z(snapshot.fetched_at),
        age_s=age_s,
        cache=cache,
        price_usdc=price_usdc(cache_hit=cache == "hit"),
        max_age_s=max_age_s,
    )
