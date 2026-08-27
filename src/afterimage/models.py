from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol


@dataclass(frozen=True)
class FetchResult:
    url: str
    final_url: str
    status: int
    body: bytes
    content_type: str


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


class Fetcher(Protocol):
    async def fetch(self, url: str) -> FetchResult: ...


class SnapshotStore(Protocol):
    async def get(self, url: str) -> Snapshot | None: ...

    async def put(self, snapshot: Snapshot) -> None: ...

    async def count(self) -> int: ...

    async def search(self, tokens: list[str], *, limit: int) -> list[Snapshot]: ...

    async def prune(self, *, now: datetime, ttl_s: int, max_snapshots: int) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


CacheState = Literal["hit", "miss"]
