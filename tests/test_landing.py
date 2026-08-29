from fastapi.testclient import TestClient

from afterimage.app import create_app
from afterimage.settings import Settings


def test_root_is_a_human_landing_page() -> None:
    client = TestClient(
        create_app(settings=Settings(public_url="https://afterimage.page"))
    )

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    text = response.text
    assert "<html" in text.lower()
    assert "AfterImage" in text
    assert "llms.txt" in text
    assert "$5" in text
    assert "/v1/billing/checkout" in text
    assert "/v1/search" in text
    assert "https://afterimage.page" in text
    assert "Authorization" in text
    assert 'id="keybox"' not in text
    assert 'href="#"' not in text
    assert "AfterImageAfterImage" not in text
    assert "Caps:" in text
    assert "About 5,000" not in text
