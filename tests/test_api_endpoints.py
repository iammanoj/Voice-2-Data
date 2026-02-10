"""Tests for frontend API endpoints."""

import pytest
import server


def test_get_table_no_data_returns_empty(client, mock_google_token):
    with mock_google_token():
        resp = client.get(
            "/api/table/test-call-1",
            headers={"Authorization": "Bearer fake-jwt"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] is None
    assert data["columns"] == []
    assert data["rows"] == []


def test_get_table_after_storing_data(client, mock_google_token):
    # Pre-store table data
    server.table_store["test-call-2"] = {
        "title": "Test Table",
        "columns": ["A", "B"],
        "rows": [{"dimension": "X", "previous_value": "1", "current_value": "2", "delta": "+100%", "is_top_contributor": False}],
        "timestamp": 1234567890.0,
    }
    with mock_google_token():
        resp = client.get(
            "/api/table/test-call-2",
            headers={"Authorization": "Bearer fake-jwt"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Table"
    assert len(data["rows"]) == 1


def test_get_table_without_auth_returns_401(client):
    resp = client.get("/api/table/x")
    assert resp.status_code == 401


def test_get_schema_returns_tables(client, mock_google_token, db):
    with mock_google_token():
        resp = client.get(
            "/api/schema",
            headers={"Authorization": "Bearer fake-jwt"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "daily_metrics" in data


def test_get_schema_without_auth_returns_401(client):
    resp = client.get("/api/schema")
    assert resp.status_code == 401
