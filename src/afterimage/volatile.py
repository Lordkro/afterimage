from __future__ import annotations

from urllib.parse import urlparse

# Stale "all systems operational" is worse than a miss. Fetch live, never index.
_VOLATILE_HOSTS = frozenset(
    {
        "status.openai.com",
        "status.anthropic.com",
        "cloudflarestatus.com",
        "githubstatus.com",
        "status.github.com",
    }
)


def is_volatile_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host in _VOLATILE_HOSTS
