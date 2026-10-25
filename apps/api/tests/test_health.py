"""Health check tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "careertwin-api"


def test_health_includes_environment() -> None:
    client = TestClient(app)
    response = client.get("/health")
    body = response.json()
    assert "environment" in body


def test_root_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "careertwin-api"
