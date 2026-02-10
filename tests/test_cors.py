"""Tests for CORS configuration."""

import server


def test_allowed_origin_gets_cors_headers(client):
    resp = client.get("/health", headers={"Origin": server.FRONTEND_ORIGIN})
    assert resp.headers.get("access-control-allow-origin") == server.FRONTEND_ORIGIN


def test_disallowed_origin_gets_no_cors(client):
    resp = client.get("/health", headers={"Origin": "http://evil.com"})
    assert resp.headers.get("access-control-allow-origin") != "http://evil.com"


def test_options_preflight_with_allowed_origin(client):
    resp = client.options(
        "/api/schema",
        headers={
            "Origin": server.FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == server.FRONTEND_ORIGIN


def test_authorization_header_is_allowed(client):
    resp = client.options(
        "/api/schema",
        headers={
            "Origin": server.FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    allowed = resp.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allowed
