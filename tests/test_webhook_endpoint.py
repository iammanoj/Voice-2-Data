"""Tests for the /vapi/webhook endpoint E2E."""

import pytest


@pytest.fixture(autouse=True)
def _no_webhook_secret():
    """Disable webhook secret for these tests to focus on logic."""
    import server

    original = server.VAPI_WEBHOOK_SECRET
    server.VAPI_WEBHOOK_SECRET = ""
    yield
    server.VAPI_WEBHOOK_SECRET = original


def test_non_tool_calls_event_returns_empty(client):
    resp = client.post(
        "/vapi/webhook",
        json={"message": {"type": "status-update"}},
    )
    assert resp.status_code == 200
    assert resp.json() == {}


def test_query_analytics_tool_call(client, db):
    payload = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "call_abc123"},
            "toolCallList": [
                {
                    "id": "tc_1",
                    "name": "query_analytics",
                    "arguments": {
                        "sql_query": "SELECT platform, dau FROM daily_metrics LIMIT 3",
                        "query_description": "DAU by platform",
                    },
                }
            ],
        }
    }
    resp = client.post("/vapi/webhook", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["toolCallId"] == "tc_1"
    assert "rows" in data["results"][0]["result"].lower() or "dau" in data["results"][0]["result"].lower()


def test_display_comparison_table_tool_call(client):
    payload = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "call_table_123"},
            "toolCallList": [
                {
                    "id": "tc_2",
                    "name": "display_comparison_table",
                    "arguments": {
                        "title": "Engagement Week-over-Week",
                        "columns": ["Dimension", "Previous", "Current", "Delta"],
                        "rows": [
                            {
                                "dimension": "Mobile DAU",
                                "previous_value": "12,450",
                                "current_value": "11,500",
                                "delta": "-7.6%",
                                "is_top_contributor": True,
                            },
                            {
                                "dimension": "Web DAU",
                                "previous_value": "45,200",
                                "current_value": "44,800",
                                "delta": "-0.9%",
                                "is_top_contributor": False,
                            },
                        ],
                    },
                }
            ],
        }
    }
    resp = client.post("/vapi/webhook", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["toolCallId"] == "tc_2"
    assert "displayed" in data["results"][0]["result"].lower()


def test_unknown_function_name(client):
    payload = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "c1"},
            "toolCallList": [
                {
                    "id": "tc_3",
                    "name": "unknown_fn",
                    "arguments": {},
                }
            ],
        }
    }
    resp = client.post("/vapi/webhook", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["toolCallId"] == "tc_3"
    assert "unknown function" in data["results"][0]["result"].lower()


def test_multiple_tool_calls_in_one_request(client, db):
    payload = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "call_multi"},
            "toolCallList": [
                {
                    "id": "tc_a",
                    "name": "query_analytics",
                    "arguments": {
                        "sql_query": "SELECT 1 as val",
                        "query_description": "simple",
                    },
                },
                {
                    "id": "tc_b",
                    "name": "display_comparison_table",
                    "arguments": {
                        "title": "Test",
                        "columns": ["A"],
                        "rows": [],
                    },
                },
            ],
        }
    }
    resp = client.post("/vapi/webhook", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 2
    ids = {r["toolCallId"] for r in data["results"]}
    assert ids == {"tc_a", "tc_b"}


def test_missing_call_id_defaults_to_unknown(client, db):
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "tc_no_call",
                    "name": "query_analytics",
                    "arguments": {
                        "sql_query": "SELECT 1 as val",
                        "query_description": "no call id",
                    },
                }
            ],
        }
    }
    resp = client.post("/vapi/webhook", json=payload)
    assert resp.status_code == 200
    # The handler should use "unknown" as call_id — just verify it doesn't crash
    data = resp.json()
    assert len(data["results"]) == 1
