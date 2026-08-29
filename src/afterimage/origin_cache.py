from __future__ import annotations

import re
from dataclasses import dataclass

_MAX_AGE = re.compile(r"(?:^|[,;\s])max-age\s*=\s*(\d+)", re.I)
_S_MAXAGE = re.compile(r"(?:^|[,;\s])s-maxage\s*=\s*(\d+)", re.I)


@dataclass(frozen=True)
class OriginCache:
    persist: bool
    reason: str | None
    max_age_s: int | None


def origin_cache_policy(*, headers: dict[str, str] | None) -> OriginCache:
    raw = ""
    for key, value in (headers or {}).items():
        if key.lower() == "cache-control":
            raw = value
            break
    tokens = {part.split("=", 1)[0].strip().lower() for part in raw.split(",") if part.strip()}
    if "no-store" in tokens:
        return OriginCache(persist=False, reason="no-store", max_age_s=None)
    if "private" in tokens:
        return OriginCache(persist=False, reason="private", max_age_s=None)
    s_max = _S_MAXAGE.search(raw)
    max_age = _MAX_AGE.search(raw)
    if s_max:
        seconds = int(s_max.group(1))
    elif max_age:
        seconds = int(max_age.group(1))
    else:
        seconds = None
    if "no-cache" in tokens and seconds is None:
        seconds = 0
    return OriginCache(persist=True, reason=None, max_age_s=seconds)
