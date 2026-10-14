from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app


def test_health_check_success(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_failure():
    mock_session = MagicMock()
    mock_session.exec.side_effect = Exception("Database connection failure")

    def override_broken_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_broken_session
    try:
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 503
            assert response.json()["status"] == "unhealthy"
            # /health is unauthenticated: the underlying error must not leak,
            # since database errors can carry connection strings.
            assert "detail" not in response.json()
            assert "Database connection failure" not in response.text
    finally:
        app.dependency_overrides.clear()
