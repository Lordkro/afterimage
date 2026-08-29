from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def new_secret() -> str:
    return "ak_live_" + secrets.token_urlsafe(24)


class KeyStore(Protocol):
    async def issue(self) -> tuple[str, str]: ...

    async def debit(self, secret: str, micros: int) -> bool: ...

    async def credit(self, key_id: str, micros: int, stripe_session: str) -> bool: ...

    async def balance(self, secret: str) -> int | None: ...

    async def ever_credited(self, secret: str) -> bool | None: ...


class MemoryKeyStore:
    def __init__(self) -> None:
        self._by_id: dict[str, dict] = {}
        self._by_hash: dict[str, str] = {}
        self._sessions: set[str] = set()
        self._n = 0

    async def issue(self) -> tuple[str, str]:
        self._n += 1
        key_id = f"key_{self._n}"
        secret = new_secret()
        digest = hash_secret(secret)
        self._by_id[key_id] = {"hash": digest, "micros": 0, "credited": 0}
        self._by_hash[digest] = key_id
        return key_id, secret

    def balance_for_secret(self, secret: str) -> int | None:
        key_id = self._by_hash.get(hash_secret(secret))
        if key_id is None:
            return None
        return int(self._by_id[key_id]["micros"])

    async def balance(self, secret: str) -> int | None:
        return self.balance_for_secret(secret)

    async def debit(self, secret: str, micros: int) -> bool:
        key_id = self._by_hash.get(hash_secret(secret))
        if key_id is None:
            return False
        row = self._by_id[key_id]
        if row["micros"] < micros:
            return False
        row["micros"] -= micros
        return True

    def apply_credit(self, key_id: str, micros: int, stripe_session: str) -> bool:
        if stripe_session in self._sessions:
            return False
        if key_id not in self._by_id:
            return False
        self._sessions.add(stripe_session)
        self._by_id[key_id]["micros"] += micros
        self._by_id[key_id]["credited"] = int(self._by_id[key_id].get("credited") or 0) + micros
        return True

    async def ever_credited(self, secret: str) -> bool | None:
        key_id = self._by_hash.get(hash_secret(secret))
        if key_id is None:
            return None
        return int(self._by_id[key_id].get("credited") or 0) > 0

    async def credit(self, key_id: str, micros: int, stripe_session: str) -> bool:
        return self.apply_credit(key_id, micros, stripe_session)


class SqliteKeyStore:
    def __init__(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                secret_hash TEXT NOT NULL UNIQUE,
                micros INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stripe_credits (
                stripe_session TEXT PRIMARY KEY,
                key_id TEXT NOT NULL,
                micros INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    async def issue(self) -> tuple[str, str]:
        key_id = "key_" + secrets.token_hex(8)
        secret = new_secret()
        self._conn.execute(
            "INSERT INTO api_keys (id, secret_hash, micros, created_at) VALUES (?, ?, 0, ?)",
            (key_id, hash_secret(secret), datetime.now(UTC).isoformat()),
        )
        self._conn.commit()
        return key_id, secret

    async def balance(self, secret: str) -> int | None:
        row = self._conn.execute(
            "SELECT micros FROM api_keys WHERE secret_hash = ?",
            (hash_secret(secret),),
        ).fetchone()
        return int(row[0]) if row else None

    async def debit(self, secret: str, micros: int) -> bool:
        cur = self._conn.execute(
            "UPDATE api_keys SET micros = micros - ? "
            "WHERE secret_hash = ? AND micros >= ?",
            (micros, hash_secret(secret), micros),
        )
        self._conn.commit()
        return cur.rowcount == 1

    async def credit(self, key_id: str, micros: int, stripe_session: str) -> bool:
        exists = self._conn.execute(
            "SELECT 1 FROM api_keys WHERE id = ?", (key_id,)
        ).fetchone()
        if exists is None:
            return False
        try:
            self._conn.execute(
                "INSERT INTO stripe_credits (stripe_session, key_id, micros, created_at) "
                "VALUES (?, ?, ?, ?)",
                (stripe_session, key_id, micros, datetime.now(UTC).isoformat()),
            )
        except sqlite3.IntegrityError:
            return False
        self._conn.execute(
            "UPDATE api_keys SET micros = micros + ? WHERE id = ?",
            (micros, key_id),
        )
        self._conn.commit()
        return True

    async def ever_credited(self, secret: str) -> bool | None:
        row = self._conn.execute(
            "SELECT id FROM api_keys WHERE secret_hash = ?",
            (hash_secret(secret),),
        ).fetchone()
        if row is None:
            return None
        credited = self._conn.execute(
            "SELECT 1 FROM stripe_credits WHERE key_id = ? LIMIT 1",
            (row[0],),
        ).fetchone()
        return credited is not None
