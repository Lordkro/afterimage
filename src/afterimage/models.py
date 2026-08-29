from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol


@dataclass(frozen=True)
class FetchResult:
    url: str
    final_url: str
    status: int
    body: bytes
    content_type: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Snapshot:
    url: str
    final_url: str
    status: int
    title: str
    text: str
    content_hash: str
    fetched_at: datetime
    content_type: str
    origin_max_age_s: int | None = None
    vary: str | None = None
    etag: str | None = None
    last_modified: str | None = None


class Fetcher(Protocol):
    async def fetch(self, url: str) -> FetchResult: ...


class SnapshotStore(Protocol):
    async def get(self, url: str) -> Snapshot | None: ...

    async def put(self, snapshot: Snapshot) -> None: ...

    async def delete(self, url: str) -> None: ...

    async def count(self) -> int: ...

    async def oldest_fetched_at(self) -> datetime | None: ...

    async def search(self, tokens: list[str], *, limit: int) -> list[Snapshot]: ...

    async def prune(self, *, now: datetime, ttl_s: int, max_snapshots: int) -> None: ...

    async def record_unmatched(self, q: str, *, indexed: int, at: datetime) -> None: ...

    async def unmatched_queries(self, *, limit: int = 50) -> list[dict]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


CacheState = Literal["hit", "miss"]
