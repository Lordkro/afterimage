from fastapi.testclient import TestClient

from afterimage.app import create_app
from tests.fakes import FakeClock, FakeFetcher, FakePage, MemorySnapshotStore

CHROME_HTML = b"""<!DOCTYPE html>
<html>
  <head><title>Background Tasks - FastAPI</title></head>
  <body>
    <a href="#main">Skip to content</a>
    <header><p>Deploy on FastAPI Cloud</p></header>
    <nav>Docs Reference</nav>
    <main id="main">
      <h1>Background Tasks</h1>
      <p>Use BackgroundTasks to run work after the response is sent.</p>
    </main>
    <footer>Copyright FastAPI</footer>
  </body>
</html>
"""


def test_extract_skips_nav_banner_and_prefers_main() -> None:
    client = TestClient(
        create_app(
            fetcher=FakeFetcher(
                {"https://example.com/bg": FakePage(body=CHROME_HTML)}
            ),
            store=MemorySnapshotStore(),
        )
    )

    text = client.get("/v1/page", params={"url": "https://example.com/bg"}).json()["text"]

    assert "BackgroundTasks to run work after the response is sent." in text
    assert "Skip to content" not in text
    assert "Deploy on FastAPI Cloud" not in text
    assert "Docs Reference" not in text
    assert "Copyright FastAPI" not in text


def test_bot_challenge_page_is_not_stored() -> None:
    html = b"""<!DOCTYPE html>
<html>
  <head><title>Just a moment...</title></head>
  <body>
    <h1>Verifying you are human. This may take a few seconds.</h1>
    <p>Cloudflare Ray ID: 9a1b2c3d4e5f</p>
  </body>
</html>"""
    body = (
        TestClient(
            create_app(
                fetcher=FakeFetcher(
                    {"https://docs.example.com/models": FakePage(body=html)}
                ),
                store=MemorySnapshotStore(),
            )
        )
        .get("/v1/page", params={"url": "https://docs.example.com/models"})
        .json()
    )
    assert body["stored"] is False
    assert body["stored_reason"] == "challenge"
    assert "Verifying you are human" in body["text"]


def test_challenge_fetch_keeps_the_previous_snapshot() -> None:
    url = "https://docs.example.com/models"
    good = FakePage(
        body=(
            b"<!DOCTYPE html><html><head><title>Models</title></head>"
            b"<body><main><p>gpt-4o context window is 128k tokens.</p></main></body></html>"
        )
    )
    wall = FakePage(
        body=(
            b"<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
            b"<body><h1>Verifying you are human</h1></body></html>"
        )
    )
    fetcher = FakeFetcher({url: good})
    store = MemorySnapshotStore()
    clock = FakeClock()
    client = TestClient(create_app(fetcher=fetcher, store=store, clock=clock))
    first = client.get("/v1/page", params={"url": url}).json()
    assert first["stored"] is True
    fetcher.pages[url] = wall
    clock.advance(1)
    second = client.get("/v1/page", params={"url": url, "max_age_s": 0}).json()
    assert second["stored"] is False
    assert second["stored_reason"] == "challenge"
    search = client.get("/v1/search", params={"q": "gpt-4o"}).json()
    assert search["indexed"] == 1
    assert "128k" in search["hits"][0]["snippet"]


def test_much_shorter_extract_does_not_replace_a_good_snapshot() -> None:
    url = "https://docs.example.com/models"
    body_text = ("gpt-4o context window is 128k tokens. " * 20).strip()
    good = FakePage(
        body=(
            b"<!DOCTYPE html><html><head><title>Models</title></head>"
            + f"<body><main><p>{body_text}</p></main></body></html>".encode()
        )
    )
    stub = FakePage(
        body=(
            b"<!DOCTYPE html><html><head><title>Models</title></head>"
            b"<body><main><p>Loading the model table.</p></main></body></html>"
        )
    )
    fetcher = FakeFetcher({url: good})
    store = MemorySnapshotStore()
    clock = FakeClock()
    client = TestClient(create_app(fetcher=fetcher, store=store, clock=clock))
    assert client.get("/v1/page", params={"url": url}).json()["stored"] is True
    fetcher.pages[url] = stub
    clock.advance(1)
    second = client.get("/v1/page", params={"url": url, "max_age_s": 0}).json()
    assert second["stored"] is False
    assert second["stored_reason"] == "thin_extract"
    search = client.get("/v1/search", params={"q": "gpt-4o"}).json()
    assert search["indexed"] == 1
    assert "128k" in search["hits"][0]["snippet"]


def test_first_fetch_under_one_thousand_chars_is_not_stored() -> None:
    paragraph = ("PayAI is building tools for agentic commerce. " * 16).strip()
    assert 400 < len(paragraph) < 1000
    html = (
        b"<!DOCTYPE html><html><head><title>Introduction - PayAI</title></head>"
        b"<body><script>" + b"x" * 8_000 + b"</script>"
        + f"<main><p>{paragraph}</p></main></body></html>".encode()
    )
    body = (
        TestClient(
            create_app(
                fetcher=FakeFetcher(
                    {"https://docs.payai.network/introduction": FakePage(body=html)}
                ),
                store=MemorySnapshotStore(),
            )
        )
        .get("/v1/page", params={"url": "https://docs.payai.network/introduction"})
        .json()
    )
    assert body["stored"] is False
    assert body["stored_reason"] == "thin_extract"
    assert "agentic commerce" in body["text"]


def test_fat_html_with_tiny_extract_is_not_stored() -> None:
    html = (
        b"<!DOCTYPE html><html><head><title>Models - Perplexity</title></head>"
        b"<body><script>" + b"x" * 80_000 + b"</script>"
        b"<main><h1>Models</h1><p>Explore the Sonar range and compare models</p>"
        b"</main></body></html>"
    )
    body = (
        TestClient(
            create_app(
                fetcher=FakeFetcher(
                    {"https://docs.perplexity.ai/docs/sonar/models": FakePage(body=html)}
                ),
                store=MemorySnapshotStore(),
            )
        )
        .get("/v1/page", params={"url": "https://docs.perplexity.ai/docs/sonar/models"})
        .json()
    )
    assert body["stored"] is False
    assert body["stored_reason"] == "thin_extract"


def test_github_spa_shell_is_not_stored() -> None:
    html = b"""<!DOCTYPE html>
<html><head><title>Releases</title></head>
<body><p>Uh oh! There was an error while loading. Please reload this page.</p></body>
</html>"""
    store = MemorySnapshotStore()
    client = TestClient(
        create_app(
            fetcher=FakeFetcher(
                {"https://github.com/fastapi/fastapi/releases": FakePage(body=html)}
            ),
            store=store,
        )
    )
    body = client.get(
        "/v1/page",
        params={"url": "https://github.com/fastapi/fastapi/releases"},
    ).json()
    assert body["stored"] is False
    assert body["stored_reason"] == "thin_extract"


def test_mkdocs_article_is_preferred_over_sidebar() -> None:
    html = b"""<!DOCTYPE html>
<html>
  <head><title>Background Tasks - FastAPI</title></head>
  <body>
    <header class="md-header">
      <a href="/"><img src="logo.svg" alt="FastAPI"></a>
      <form><input type="text" name="q"></form>
      <p>Deploy on FastAPI Cloud</p>
    </header>
    <main class="md-main">
      <nav class="md-nav" aria-label="Navigation">
        <ul>
          <li>Path Parameters</li>
          <li>Query Parameters</li>
          <li>Background Tasks</li>
        </ul>
      </nav>
      <article class="md-content__inner md-typeset">
        <h1>Background Tasks</h1>
        <p>You can define background tasks to be run after returning a response.</p>
      </article>
    </main>
  </body>
</html>"""
    text = (
        TestClient(
            create_app(
                fetcher=FakeFetcher(
                    {"https://example.com/bg-article": FakePage(body=html)}
                ),
                store=MemorySnapshotStore(),
            )
        )
        .get("/v1/page", params={"url": "https://example.com/bg-article"})
        .json()["text"]
    )
    assert "You can define background tasks to be run after returning a response." in text
    assert "Path Parameters" not in text
    assert "Query Parameters" not in text
    assert "Deploy on FastAPI Cloud" not in text


def test_mkdocs_content_div_is_extracted() -> None:
    html = b"""<!DOCTYPE html>
<html>
  <head><title>Background Tasks - FastAPI</title></head>
  <body>
    <header>nav chrome</header>
    <div class="md-content">
      <p>Use BackgroundTasks to run work after the response is sent.</p>
    </div>
  </body>
</html>"""
    text = (
        TestClient(
            create_app(
                fetcher=FakeFetcher(
                    {"https://example.com/md": FakePage(body=html)}
                ),
                store=MemorySnapshotStore(),
            )
        )
        .get("/v1/page", params={"url": "https://example.com/md"})
        .json()["text"]
    )
    assert "BackgroundTasks to run work after the response is sent." in text
