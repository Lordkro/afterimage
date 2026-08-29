from pathlib import Path

from afterimage.volatile import is_volatile_url

SEED = Path(__file__).resolve().parents[1] / "scripts" / "seed_urls.txt"
_TRAINING_DATA_MARKERS = (
    "docs.python.org",
    "peps.python.org",
    "git-scm.com",
    "developer.mozilla.org",
    "datatracker.ietf.org",
    "www.rfc-editor.org",
    "httpwg.org",
)


def _seed_urls() -> list[str]:
    urls: list[str] = []
    for raw in SEED.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def test_seed_list_is_the_moving_class() -> None:
    urls = _seed_urls()
    blob = "\n".join(urls)
    assert len(urls) >= 40
    for url in urls:
        assert url.startswith("https://")
        assert not is_volatile_url(url)
        for marker in _TRAINING_DATA_MARKERS:
            assert marker not in url
    assert "docs.x402.org" in blob
    assert "specification/2025" in blob
    assert "/docs/models" in blob or "/models" in blob
    assert "pricing" in blob
    assert "release-notes" in blob or "changelog" in blob
    assert "deprecations" in blob
    assert "rate-limits" in blob
    assert "pypi.org/pypi/" in blob
