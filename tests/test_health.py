"""Tests for the /health endpoint."""


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "db_exists" in data


def test_health_has_no_auth_requirement(client):
    # No Authorization header — should still return 200
    resp = client.get("/health")
    assert resp.status_code == 200
