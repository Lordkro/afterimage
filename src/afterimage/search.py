from __future__ import annotations

import re
from datetime import datetime

from fastapi import HTTPException
from pydantic import BaseModel, Field

from afterimage.models import Clock, Snapshot, SnapshotStore
from afterimage.pages import iso_z, prune_corpus
from afterimage.pricing import SEARCH_USDC
from afterimage.settings import Settings

DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50
SNIPPET_RADIUS = 80


class SearchHit(BaseModel):
    url: str
    title: str
    snippet: str
    hash: str
    fetched_at: str
    age_s: int
    status: int
    score: float


class SearchResponse(BaseModel):
    q: str
    indexed: int
    hits: list[SearchHit]
    price_usdc: str = SEARCH_USDC
    max_age_s: int | None = None
    limit: int = Field(default=DEFAULT_SEARCH_LIMIT)


def tokenize(query: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", query.lower()) if token]


def score_snapshot(snapshot: Snapshot, tokens: list[str]) -> float:
    title = snapshot.title.lower()
    url = snapshot.url.lower()
    text = snapshot.text.lower()
    score = 0.0
    for token in tokens:
        if token in title:
            score += 3.0
        if token in url:
            score += 2.0
        if token in text:
            score += 1.0
    phrase = " ".join(tokens)
    if len(tokens) > 1 and phrase in text:
        score += 0.5
    return score


def snippet_for(snapshot: Snapshot, tokens: list[str]) -> str:
    text = re.sub(r"\s+", " ", snapshot.text).strip()
    if not text:
        return snapshot.title
    lower = text.lower()
    title = (snapshot.title or "").strip().lower()
    skip = len(title) if title and lower.startswith(title) else 0
    index = -1
    for token in tokens:
        found = lower.find(token, skip)
        if found == -1:
            found = lower.find(token)
        if found != -1 and (index == -1 or found < index):
            index = found
    if index == -1:
        return text[: SNIPPET_RADIUS * 2]
    start = max(0, index - SNIPPET_RADIUS)
    end = min(len(text), index + SNIPPET_RADIUS)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet


async def search_corpus(
    q: str,
    *,
    store: SnapshotStore,
    clock: Clock,
    limit: int = DEFAULT_SEARCH_LIMIT,
    max_age_s: int | None = None,
    settings: Settings | None = None,
) -> SearchResponse:
    settings = settings or Settings()
    q = q.strip()
    tokens = tokenize(q)
    if not tokens:
        raise HTTPException(status_code=422, detail="q must contain a searchable term")
    if limit < 1:
        limit = DEFAULT_SEARCH_LIMIT
    limit = min(limit, MAX_SEARCH_LIMIT)
    await prune_corpus(store, settings, clock)
    now = clock.now()
    indexed = await store.count()
    candidates = await store.search(tokens, limit=MAX_SEARCH_LIMIT)
    ranked: list[tuple[float, datetime, Snapshot]] = []
    for snapshot in candidates:
        age_s = int((now - snapshot.fetched_at).total_seconds())
        if max_age_s is not None and age_s > max_age_s:
            continue
        score = score_snapshot(snapshot, tokens)
        if score <= 0:
            continue
        ranked.append((score, snapshot.fetched_at, snapshot))
    ranked.sort(key=lambda item: (-item[0], -item[1].timestamp()))
    hits = [
        SearchHit(
            url=snapshot.url,
            title=snapshot.title,
            snippet=snippet_for(snapshot, tokens),
            hash=snapshot.content_hash,
            fetched_at=iso_z(snapshot.fetched_at),
            age_s=max(0, int((now - snapshot.fetched_at).total_seconds())),
            status=snapshot.status,
            score=round(score, 3),
        )
        for score, _fetched_at, snapshot in ranked[:limit]
    ]
    return SearchResponse(
        q=q,
        indexed=indexed,
        hits=hits,
        price_usdc=SEARCH_USDC,
        max_age_s=max_age_s,
        limit=limit,
    )
