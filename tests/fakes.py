from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from afterimage.models import FetchResult, Snapshot


@dataclass
class FakePage:
    body: bytes
    status: int = 200
    content_type: str = "text/html; charset=utf-8"
    final_url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


class FakeFetcher:
    def __init__(self, pages: dict[str, FakePage]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    async def fetch(self, url: str) -> FetchResult:
        self.calls.append(url)
        page = self.pages[url]
        return FetchResult(
            url=url,
            final_url=page.final_url or url,
            status=page.status,
            body=page.body,
            content_type=page.content_type,
            headers=page.headers,
        )


class MemorySnapshotStore:
    def __init__(self) -> None:
        self._by_url: dict[str, Snapshot] = {}

    async def get(self, url: str) -> Snapshot | None:
        return self._by_url.get(url)

    async def put(self, snapshot: Snapshot) -> None:
        self._by_url[snapshot.url] = snapshot

    async def delete(self, url: str) -> None:
        self._by_url.pop(url, None)

    async def count(self) -> int:
        return len(self._by_url)

    async def oldest_fetched_at(self) -> datetime | None:
        if not self._by_url:
            return None
        return min(item.fetched_at for item in self._by_url.values())

    async def search(self, tokens: list[str], *, limit: int) -> list[Snapshot]:
        hits: list[Snapshot] = []
        for snapshot in self._by_url.values():
            haystack = f"{snapshot.url}\n{snapshot.title}\n{snapshot.text}".lower()
            if all(token in haystack for token in tokens):
                hits.append(snapshot)
            if len(hits) >= limit:
                break
        return hits

    async def prune(self, *, now: datetime, ttl_s: int, max_snapshots: int) -> None:
        if ttl_s > 0:
            expired = [
                url
                for url, snapshot in self._by_url.items()
                if (now - snapshot.fetched_at).total_seconds() > ttl_s
            ]
            for url in expired:
                del self._by_url[url]
        if max_snapshots <= 0:
            return
        while len(self._by_url) > max_snapshots:
            oldest = min(self._by_url.values(), key=lambda item: item.fetched_at)
            del self._by_url[oldest.url]


class FakeClock:
    def __init__(self, now: str = "2026-08-27T18:41:02Z") -> None:
        self._now = datetime.fromisoformat(now.replace("Z", "+00:00")).astimezone(UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: int) -> None:
        from datetime import timedelta

        self._now = self._now + timedelta(seconds=seconds)
