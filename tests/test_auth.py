"""Tests for Google JWT authentication."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest


def test_missing_authorization_header_returns_401(client):
    resp = client.get("/api/schema")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Missing authentication token"


def test_non_bearer_token_returns_401(client):
    resp = client.get("/api/schema", headers={"Authorization": "Basic xyz"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Missing authentication token"


def test_invalid_token_returns_401(client):
    """A token that Google rejects should return 401."""
    import urllib.error

    with patch(
        "server.urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(None, 401, "Unauthorized", {}, None),
    ):
        resp = client.get(
            "/api/schema", headers={"Authorization": "Bearer invalid-token"}
        )
    assert resp.status_code == 401


def test_valid_token_passes(client, mock_google_token):
    """A valid token should allow access to protected endpoints."""
    with mock_google_token():
        resp = client.get(
            "/api/schema", headers={"Authorization": "Bearer valid-token"}
        )
    # May be 200 or 500 depending on DB — but not 401
    assert resp.status_code != 401


def test_audience_mismatch_returns_401(client):
    """Token with wrong audience should be rejected."""
    import server

    original = server.GOOGLE_CLIENT_ID
    server.GOOGLE_CLIENT_ID = "my-real-client-id"

    payload = {
        "aud": "wrong-client-id",
        "exp": str(int(time.time() + 3600)),
        "email": "user@test.com",
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("server.urllib.request.urlopen", return_value=mock_resp):
        resp = client.get(
            "/api/schema", headers={"Authorization": "Bearer aud-mismatch-token"}
        )

    server.GOOGLE_CLIENT_ID = original
    assert resp.status_code == 401
    assert "audience" in resp.json()["detail"].lower()


def test_expired_token_returns_401(client):
    """Token with past expiration should be rejected from cache."""
    import server

    # Pre-populate cache with an expired token
    server._token_cache["expired-tok"] = ("user@test.com", time.time() - 100)

    # urlopen should be called again since cache is expired, and it should fail
    import urllib.error

    with patch(
        "server.urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(None, 401, "Unauthorized", {}, None),
    ):
        resp = client.get(
            "/api/schema", headers={"Authorization": "Bearer expired-tok"}
        )
    assert resp.status_code == 401


def test_token_cache_works(client, mock_google_token):
    """Calling twice with the same token should only call urlopen once."""
    with mock_google_token() as mock_urlopen:
        client.get("/api/schema", headers={"Authorization": "Bearer cached-token"})
        client.get("/api/schema", headers={"Authorization": "Bearer cached-token"})
        assert mock_urlopen.call_count == 1
