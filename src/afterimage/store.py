from __future__ import annotations

import asyncio
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from afterimage.extract import fts_text
from afterimage.models import Snapshot
from afterimage.volatile import drop_reason


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
        self._ensure_columns()
        self._backfill_fts()
        self._lock = asyncio.Lock()

    def _ensure_columns(self) -> None:
        cols = {row[1] for row in self._conn.execute("PRAGMA table_info(snapshots)")}
        wanted = {
            "origin_max_age_s": "INTEGER",
            "vary": "TEXT",
            "etag": "TEXT",
            "last_modified": "TEXT",
        }
        for name, typ in wanted.items():
            if name not in cols:
                self._conn.execute(f"ALTER TABLE snapshots ADD COLUMN {name} {typ}")
        self._conn.commit()

    def _backfill_fts(self) -> None:
        count = self._conn.execute("SELECT COUNT(*) FROM snapshots_fts").fetchone()
        if count and count[0]:
            self._reindex_fts()
            return
        self._reindex_fts()

    def _reindex_fts(self) -> None:
        self._conn.execute("DELETE FROM snapshots_fts")
        rows = self._conn.execute(
            "SELECT url, title, text, content_type FROM snapshots"
        ).fetchall()
        for url, title, text, content_type in rows:
            self._conn.execute(
                "INSERT INTO snapshots_fts (url, title, text) VALUES (?, ?, ?)",
                (url, title, fts_text(text, content_type or "")),
            )
        self._conn.commit()

    async def get(self, url: str) -> Snapshot | None:
        async with self._lock:
            row = self._conn.execute(
                "SELECT url, final_url, status, title, text, content_hash, fetched_at, "
                "content_type, origin_max_age_s, vary, etag, last_modified "
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
                    url, final_url, status, title, text, content_hash, fetched_at,
                    content_type, origin_max_age_s, vary, etag, last_modified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    final_url = excluded.final_url,
                    status = excluded.status,
                    title = excluded.title,
                    text = excluded.text,
                    content_hash = excluded.content_hash,
                    fetched_at = excluded.fetched_at,
                    content_type = excluded.content_type,
                    origin_max_age_s = excluded.origin_max_age_s,
                    vary = excluded.vary,
                    etag = excluded.etag,
                    last_modified = excluded.last_modified
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
                    snapshot.origin_max_age_s,
                    snapshot.vary,
                    snapshot.etag,
                    snapshot.last_modified,
                ),
            )
            self._conn.execute(
                "DELETE FROM snapshots_fts WHERE url = ?", (snapshot.url,)
            )
            self._conn.execute(
                "INSERT INTO snapshots_fts (url, title, text) VALUES (?, ?, ?)",
                (
                    snapshot.url,
                    snapshot.title,
                    fts_text(snapshot.text, snapshot.content_type),
                ),
            )
            self._conn.commit()

    async def delete(self, url: str) -> None:
        async with self._lock:
            self._delete_urls([url])
            self._conn.commit()

    async def count(self) -> int:
        async with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()
        return int(row[0]) if row else 0

    async def oldest_fetched_at(self) -> datetime | None:
        async with self._lock:
            row = self._conn.execute("SELECT MIN(fetched_at) FROM snapshots").fetchone()
        if not row or not row[0]:
            return None
        return datetime.fromisoformat(str(row[0])).astimezone(UTC)

    async def search(self, tokens: list[str], *, limit: int) -> list[Snapshot]:
        if not tokens:
            return []
        match = " AND ".join('"' + token.replace('"', "") + '"' for token in tokens)
        async with self._lock:
            rows = self._conn.execute(
                """
                SELECT s.url, s.final_url, s.status, s.title, s.text, s.content_hash,
                       s.fetched_at, s.content_type, s.origin_max_age_s,
                       s.vary, s.etag, s.last_modified
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
            dropped = [
                row[0]
                for row in self._conn.execute("SELECT url, final_url FROM snapshots")
                if drop_reason(row[0]) or drop_reason(row[1])
            ]
            self._delete_urls(dropped)
            if ttl_s > 0:
                cutoff = (now.astimezone(UTC) - timedelta(seconds=ttl_s)).isoformat()
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
            origin_max_age_s=int(row[8]) if len(row) > 8 and row[8] is not None else None,
            vary=row[9] if len(row) > 9 else None,
            etag=row[10] if len(row) > 10 else None,
            last_modified=row[11] if len(row) > 11 else None,
        )
