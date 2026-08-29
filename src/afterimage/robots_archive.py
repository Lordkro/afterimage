from __future__ import annotations

import re

_META = re.compile(r"<meta\b[^>]*>", re.I)
_META_NAME = re.compile(r"\bname\s*=\s*['\"](robots|googlebot)['\"]", re.I)
_META_CONTENT = re.compile(r"\bcontent\s*=\s*['\"]([^'\"]+)['\"]", re.I)


def robots_tokens(value: str) -> set[str]:
    parts: list[str] = []
    for chunk in value.split(","):
        token = chunk.split(":", 1)[-1].strip().lower()
        if token:
            parts.append(token)
    return set(parts)


def forbids_archive(
    *,
    headers: dict[str, str] | None,
    body: bytes,
    content_type: str,
) -> bool:
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    tag = headers.get("x-robots-tag") or ""
    if _disallow(robots_tokens(tag)):
        return True
    if "html" not in (content_type or "").lower():
        return False
    html = body.decode("utf-8", errors="replace")
    for meta in _META.finditer(html):
        tag = meta.group(0)
        if not _META_NAME.search(tag):
            continue
        match = _META_CONTENT.search(tag)
        if match and _disallow(robots_tokens(match.group(1))):
            return True
    return False


def _disallow(tokens: set[str]) -> bool:
    return bool(tokens & {"noarchive", "none"})
