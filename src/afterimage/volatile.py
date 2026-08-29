from __future__ import annotations

from pathlib import Path
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
# In every model's training data. Fetch live if asked; do not sell a copy.
_TRAINING_HOSTS = frozenset(
    {
        "docs.python.org",
        "peps.python.org",
        "git-scm.com",
        "developer.mozilla.org",
        "datatracker.ietf.org",
        "rfc-editor.org",
        "httpwg.org",
        "nodejs.org",
        "typescriptlang.org",
        "playwright.dev",
        "owasp.org",
        "sqlite.org",
        "redis.io",
        "json-schema.org",
        "packaging.python.org",
        "jsonrpc.org",
        "swagger.io",
        "cwe.mitre.org",
        "json.schemastore.org",
    }
)


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def is_volatile_url(url: str) -> bool:
    return _host(url) in _VOLATILE_HOSTS


_EXAMPLE_HOSTS = frozenset({"example.com", "example.org", "example.net"})


def is_training_data_url(url: str) -> bool:
    host = _host(url)
    if host in _TRAINING_HOSTS:
        return True
    return host.endswith(".owasp.org")


def is_example_fixture_url(url: str) -> bool:
    """IANA example hosts at the site root — ping/docs artifacts, not corpus."""
    if _host(url) not in _EXAMPLE_HOSTS:
        return False
    path = (urlparse(url).path or "/").rstrip("/") or "/"
    return path in {"/", "/index.html"}


def load_seed_urls() -> frozenset[str]:
    candidates = [
        Path(__file__).with_name("seed_urls.txt"),
        Path(__file__).resolve().parents[2] / "scripts" / "seed_urls.txt",
        Path("/app/scripts/seed_urls.txt"),
        Path.cwd() / "scripts" / "seed_urls.txt",
    ]
    for path in candidates:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        urls = {
            line.strip()
            for line in raw.splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        if urls:
            return frozenset(urls)
    return frozenset()


def drop_reason(url: str) -> str | None:
    if is_volatile_url(url):
        return "volatile"
    if is_training_data_url(url):
        return "training_data"
    if is_example_fixture_url(url):
        return "example"
    return None
