"""Tests for VAPI webhook secret authentication."""

from unittest.mock import patch

import pytest


DUMMY_PAYLOAD = {"message": {"type": "status-update"}}


def test_no_secret_header_returns_401(client):
    """Missing x-vapi-secret header should return 401."""
    import server

    original = server.VAPI_WEBHOOK_SECRET
    server.VAPI_WEBHOOK_SECRET = "a-real-secret"
    try:
        resp = client.post("/vapi/webhook", json=DUMMY_PAYLOAD)
        assert resp.status_code == 401
    finally:
        server.VAPI_WEBHOOK_SECRET = original


def test_wrong_secret_returns_401(client):
    """Wrong x-vapi-secret should return 401."""
    import server

    original = server.VAPI_WEBHOOK_SECRET
    server.VAPI_WEBHOOK_SECRET = "correct-secret"
    try:
        resp = client.post(
            "/vapi/webhook",
            json=DUMMY_PAYLOAD,
            headers={"x-vapi-secret": "wrong-secret"},
        )
        assert resp.status_code == 401
    finally:
        server.VAPI_WEBHOOK_SECRET = original


def test_correct_secret_processes_request(client):
    """Correct x-vapi-secret should allow the request through."""
    import server

    original = server.VAPI_WEBHOOK_SECRET
    server.VAPI_WEBHOOK_SECRET = "correct-secret"
    try:
        resp = client.post(
            "/vapi/webhook",
            json=DUMMY_PAYLOAD,
            headers={"x-vapi-secret": "correct-secret"},
        )
        assert resp.status_code == 200
    finally:
        server.VAPI_WEBHOOK_SECRET = original


def test_empty_webhook_secret_skips_check(client):
    """When VAPI_WEBHOOK_SECRET is empty, any request should pass."""
    import server

    original = server.VAPI_WEBHOOK_SECRET
    server.VAPI_WEBHOOK_SECRET = ""
    try:
        resp = client.post("/vapi/webhook", json=DUMMY_PAYLOAD)
        assert resp.status_code == 200
    finally:
        server.VAPI_WEBHOOK_SECRET = original
