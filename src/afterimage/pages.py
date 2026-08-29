from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from afterimage.extract import extract_readable, unusable_extract
from afterimage.origin_cache import origin_cache_policy
from afterimage.robots_archive import forbids_archive
from afterimage.hashing import sha256_bytes
from afterimage.models import Clock, Fetcher, Snapshot, SnapshotStore
from afterimage.pricing import price_usdc
from afterimage.settings import Settings
from afterimage.urls import require_public_http_url

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
    truncated: bool = False
    stored: bool = True
    stored_reason: str | None = None
    origin_max_age_s: int | None = None
    vary: str | None = None
    etag: str | None = None
    last_modified: str | None = None


def iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return text[:max_chars]
    return text[: max_chars - 1].rstrip() + "…"


async def prune_corpus(store: SnapshotStore, settings: Settings, clock: Clock) -> None:
    await store.prune(
        now=clock.now(),
        ttl_s=settings.snapshot_ttl_s,
        max_snapshots=settings.max_snapshots,
    )


async def fresh_snapshot(
    url: str,
    *,
    max_age_s: int,
    store: SnapshotStore,
    clock: Clock,
    ttl_s: int = 0,
) -> Snapshot | None:
    url = require_public_http_url(url)
    existing = await store.get(url)
    if existing is None:
        return None
    age_s = int((clock.now() - existing.fetched_at).total_seconds())
    if ttl_s > 0 and age_s > ttl_s:
        return None
    if existing.origin_max_age_s is not None and age_s >= existing.origin_max_age_s:
        return None
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
    settings: Settings | None = None,
) -> PageResponse:
    settings = settings or Settings()
    url = require_public_http_url(url)
    if max_age_s < 0:
        max_age_s = 0
    await prune_corpus(store, settings, clock)
    now = clock.now()
    existing = await fresh_snapshot(
        url,
        max_age_s=max_age_s,
        store=store,
        clock=clock,
        ttl_s=settings.snapshot_ttl_s,
    )
    if existing is not None:
        truncated = _looks_truncated(existing.text, settings.max_text_chars)
        return _view(
            existing,
            now=now,
            cache="hit",
            max_age_s=max_age_s,
            truncated=truncated,
            stored=True,
        )

    fetched = await fetcher.fetch(url)
    title, raw_text = extract_readable(fetched.body, fetched.content_type)
    text = truncate_text(raw_text, settings.max_text_chars)
    truncated = len(raw_text) > len(text)
    policy = origin_cache_policy(headers=fetched.headers, now=now)
    noarchive = forbids_archive(
        headers=fetched.headers,
        body=fetched.body,
        content_type=fetched.content_type,
    )
    stored_reason = None
    if noarchive:
        stored_reason = "noarchive"
    elif not policy.persist:
        stored_reason = policy.reason
    elif snapshot_status_blocks_store(fetched.status, settings.persist_error_pages):
        stored_reason = "http_error"
    elif unusable_extract(title, text):
        stored_reason = "thin_extract"
    snapshot = Snapshot(
        url=url,
        final_url=fetched.final_url,
        status=fetched.status,
        title=title,
        text=text,
        content_hash=sha256_bytes(fetched.body),
        fetched_at=now,
        content_type=fetched.content_type,
        origin_max_age_s=policy.max_age_s,
        vary=_header(fetched.headers, "vary"),
        etag=_header(fetched.headers, "etag"),
        last_modified=_header(fetched.headers, "last-modified"),
    )
    keep = stored_reason is None
    if keep:
        await store.put(snapshot)
        await prune_corpus(store, settings, clock)
    else:
        await store.delete(url)
    return _view(
        snapshot,
        now=now,
        cache="miss",
        max_age_s=max_age_s,
        truncated=truncated,
        stored=keep,
        stored_reason=stored_reason,
    )


def snapshot_status_blocks_store(status: int, persist_error_pages: bool) -> bool:
    return status >= 400 and not persist_error_pages


def _looks_truncated(text: str, max_chars: int) -> bool:
    if max_chars <= 0 or len(text) < max_chars - 1:
        return False
    return text.endswith("…")


def _view(
    snapshot: Snapshot,
    *,
    now: datetime,
    cache: str,
    max_age_s: int,
    truncated: bool = False,
    stored: bool = True,
    stored_reason: str | None = None,
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
        truncated=truncated,
        stored=stored,
        stored_reason=stored_reason,
        origin_max_age_s=snapshot.origin_max_age_s,
        vary=snapshot.vary,
        etag=snapshot.etag,
        last_modified=snapshot.last_modified,
    )


def _header(headers: dict[str, str] | None, name: str) -> str | None:
    if not headers:
        return None
    value = headers.get(name.lower()) or headers.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
