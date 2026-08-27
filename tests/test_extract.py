from fastapi.testclient import TestClient

from afterimage.app import create_app
from tests.fakes import FakeFetcher, FakePage, MemorySnapshotStore

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
