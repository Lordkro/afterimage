from fastapi.testclient import TestClient

from already.app import create_app


def test_health_reports_ready() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "already"
