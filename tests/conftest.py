"""Shared fixtures for backend tests."""

import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _clear_server_state():
    """Clear in-memory state between tests."""
    import server

    server.table_store.clear()
    server.sse_queues.clear()
    server._token_cache.clear()
    yield
    server.table_store.clear()
    server.sse_queues.clear()
    server._token_cache.clear()


@pytest.fixture()
def client():
    """FastAPI TestClient with the server app."""
    import server

    return TestClient(server.app)


@pytest.fixture()
def db(tmp_path):
    """Create a temporary SQLite DB with test data and patch DB_PATH."""
    db_path = str(tmp_path / "test_engagement.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE daily_metrics (
            date TEXT, platform TEXT, segment TEXT,
            dau INTEGER, wau INTEGER, mau INTEGER,
            session_duration_avg REAL, sessions_per_user REAL,
            bounce_rate REAL, pages_per_session REAL,
            PRIMARY KEY (date, platform, segment)
        )
        """
    )
    # Insert some test rows
    for i in range(5):
        conn.execute(
            "INSERT INTO daily_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"2026-01-{10 + i:02d}",
                "mobile",
                "free",
                10000 + i * 100,
                50000,
                200000,
                5.5,
                2.3,
                0.35,
                3.2,
            ),
        )
    conn.commit()
    conn.close()

    import server

    original = server.DB_PATH
    server.DB_PATH = db_path
    yield db_path
    server.DB_PATH = original


def _make_google_tokeninfo_response(
    email="user@test.com",
    aud=None,
    exp=None,
):
    """Build a fake Google tokeninfo JSON payload."""
    import time

    import server

    return {
        "iss": "https://accounts.google.com",
        "aud": aud or server.GOOGLE_CLIENT_ID or "test-client-id",
        "exp": str(int(exp or time.time() + 3600)),
        "email": email,
        "name": "Test User",
        "picture": "https://example.com/photo.jpg",
    }


@pytest.fixture()
def mock_google_token():
    """Patch urllib.request.urlopen to return a fake tokeninfo response."""

    @contextmanager
    def _mock(email="user@test.com", aud=None, exp=None):
        payload = _make_google_tokeninfo_response(email=email, aud=aud, exp=exp)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("server.urllib.request.urlopen", return_value=mock_resp) as m:
            yield m

    return _mock


@pytest.fixture()
def valid_auth_header(mock_google_token):
    """Returns a valid Authorization header dict with mocked Google verification."""
    return {"Authorization": "Bearer fake-google-jwt"}


@pytest.fixture()
def valid_vapi_secret_header():
    """Returns the correct x-vapi-secret header."""
    import server

    secret = server.VAPI_WEBHOOK_SECRET or "test-webhook-secret"
    return {"x-vapi-secret": secret}
