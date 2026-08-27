from __future__ import annotations

import asyncio
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from afterimage.models import Snapshot


class SqliteSnapshotStore:
    def __init__(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                url TEXT PRIMARY KEY,
                final_url TEXT NOT NULL,
                status INTEGER NOT NULL,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                content_type TEXT NOT NULL
            )
            """
        )
        self._conn.commit()
        self._conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS snapshots_fts USING fts5(
                url, title, text, tokenize = 'porter unicode61'
            )
            """
        )
        self._conn.commit()
        self._backfill_fts()
        self._lock = asyncio.Lock()

    def _backfill_fts(self) -> None:
        count = self._conn.execute("SELECT COUNT(*) FROM snapshots_fts").fetchone()
        if count and count[0]:
            return
        rows = self._conn.execute("SELECT url, title, text FROM snapshots").fetchall()
        for url, title, text in rows:
            self._conn.execute(
                "INSERT INTO snapshots_fts (url, title, text) VALUES (?, ?, ?)",
                (url, title, text),
            )
        if rows:
            self._conn.commit()

    async def get(self, url: str) -> Snapshot | None:
        async with self._lock:
            row = self._conn.execute(
                "SELECT url, final_url, status, title, text, content_hash, fetched_at, content_type "
                "FROM snapshots WHERE url = ?",
                (url,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_snapshot(row)

    async def put(self, snapshot: Snapshot) -> None:
        async with self._lock:
            self._conn.execute(
                """
                INSERT INTO snapshots (
                    url, final_url, status, title, text, content_hash, fetched_at, content_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    final_url = excluded.final_url,
                    status = excluded.status,
                    title = excluded.title,
                    text = excluded.text,
                    content_hash = excluded.content_hash,
                    fetched_at = excluded.fetched_at,
                    content_type = excluded.content_type
                """,
                (
                    snapshot.url,
                    snapshot.final_url,
                    snapshot.status,
                    snapshot.title,
                    snapshot.text,
                    snapshot.content_hash,
                    snapshot.fetched_at.astimezone(UTC).isoformat(),
                    snapshot.content_type,
                ),
            )
            self._conn.execute(
                "DELETE FROM snapshots_fts WHERE url = ?", (snapshot.url,)
            )
            self._conn.execute(
                "INSERT INTO snapshots_fts (url, title, text) VALUES (?, ?, ?)",
                (snapshot.url, snapshot.title, snapshot.text),
            )
            self._conn.commit()

    async def count(self) -> int:
        async with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()
        return int(row[0]) if row else 0

    async def search(self, tokens: list[str], *, limit: int) -> list[Snapshot]:
        if not tokens:
            return []
        match = " AND ".join('"' + token.replace('"', "") + '"' for token in tokens)
        async with self._lock:
            rows = self._conn.execute(
                """
                SELECT s.url, s.final_url, s.status, s.title, s.text, s.content_hash,
                       s.fetched_at, s.content_type
                FROM snapshots s
                WHERE s.url IN (
                    SELECT url FROM snapshots_fts WHERE snapshots_fts MATCH ?
                )
                LIMIT ?
                """,
                (match, limit),
            ).fetchall()
        return [self._row_to_snapshot(row) for row in rows]

    async def prune(self, *, now: datetime, ttl_s: int, max_snapshots: int) -> None:
        async with self._lock:
            if ttl_s > 0:
                cutoff = now.astimezone(UTC).isoformat()
                urls = [
                    row[0]
                    for row in self._conn.execute(
                        "SELECT url FROM snapshots WHERE fetched_at < ?",
                        (cutoff,),
                    ).fetchall()
                ]
                self._delete_urls(urls)
            if max_snapshots > 0:
                count_row = self._conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()
                extra = int(count_row[0]) - max_snapshots if count_row else 0
                if extra > 0:
                    oldest = [
                        row[0]
                        for row in self._conn.execute(
                            "SELECT url FROM snapshots ORDER BY fetched_at ASC LIMIT ?",
                            (extra,),
                        ).fetchall()
                    ]
                    self._delete_urls(oldest)
            self._conn.commit()

    def _delete_urls(self, urls: list[str]) -> None:
        for url in urls:
            self._conn.execute("DELETE FROM snapshots WHERE url = ?", (url,))
            self._conn.execute("DELETE FROM snapshots_fts WHERE url = ?", (url,))

    def _row_to_snapshot(self, row: tuple) -> Snapshot:
        fetched_at = datetime.fromisoformat(row[6])
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=UTC)
        return Snapshot(
            url=row[0],
            final_url=row[1],
            status=row[2],
            title=row[3],
            text=row[4],
            content_hash=row[5],
            fetched_at=fetched_at.astimezone(UTC),
            content_type=row[7],
        )
