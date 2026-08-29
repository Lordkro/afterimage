from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

_MAX_AGE = re.compile(r"(?:^|[,;\s])max-age\s*=\s*(\d+)", re.I)
_S_MAXAGE = re.compile(r"(?:^|[,;\s])s-maxage\s*=\s*(\d+)", re.I)


@dataclass(frozen=True)
class OriginCache:
    persist: bool
    reason: str | None
    max_age_s: int | None


def _header(headers: dict[str, str], name: str) -> str:
    needle = name.lower()
    for key, value in headers.items():
        if key.lower() == needle:
            return value
    return ""


def _http_date(value: str) -> datetime | None:
    if not value.strip():
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def origin_cache_policy(
    *,
    headers: dict[str, str] | None,
    now: datetime | None = None,
) -> OriginCache:
    headers = headers or {}
    vary = _header(headers, "vary")
    if any(part.strip() == "*" for part in vary.split(",")):
        return OriginCache(persist=False, reason="vary", max_age_s=None)

    raw = _header(headers, "cache-control")
    tokens = {
        part.split("=", 1)[0].strip().lower()
        for part in raw.split(",")
        if part.strip()
    }
    lifetime: int | None = None
    if raw:
        s_max = _S_MAXAGE.search(raw)
        max_age = _MAX_AGE.search(raw)
        if s_max:
            lifetime = int(s_max.group(1))
        elif max_age:
            lifetime = int(max_age.group(1))
    else:
        expires = _http_date(_header(headers, "expires"))
        date = _http_date(_header(headers, "date"))
        if expires is not None:
            start = date if date is not None else (now or datetime.now(UTC))
            lifetime = max(0, int((expires - start).total_seconds()))

    # AfterImage is a snapshot index, not a shared HTTP cache. no-store/private
    # on public docs (Mintlify/Next defaults) still get indexed; /v1/page will
    # not reuse them as a cache hit. noarchive and Vary: * remain opt-outs.
    if "no-store" in tokens or "private" in tokens or "no-cache" in tokens:
        lifetime = 0
    elif lifetime is None and "must-revalidate" in tokens:
        lifetime = 0

    remaining = lifetime
    if remaining is not None:
        try:
            age = int(_header(headers, "age").strip() or "0")
        except ValueError:
            age = 0
        remaining = max(0, remaining - max(age, 0))

    return OriginCache(persist=True, reason=None, max_age_s=remaining)
