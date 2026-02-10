"""Tests for SQL validation safety."""

import server


def test_valid_select_passes():
    assert server.validate_sql("SELECT * FROM daily_metrics LIMIT 5") is None


def test_drop_blocked():
    result = server.validate_sql("DROP TABLE daily_metrics")
    assert result is not None
    assert "blocked" in result.lower() or "SELECT" in result


def test_delete_blocked():
    result = server.validate_sql("DELETE FROM daily_metrics")
    assert result is not None


def test_insert_blocked():
    result = server.validate_sql("INSERT INTO daily_metrics VALUES (1,2,3)")
    assert result is not None


def test_update_blocked():
    result = server.validate_sql("UPDATE daily_metrics SET dau=0")
    assert result is not None


def test_non_select_rejected():
    result = server.validate_sql("PRAGMA table_info(daily_metrics)")
    assert result is not None


def test_multiple_statements_rejected():
    result = server.validate_sql("SELECT 1; DROP TABLE x")
    assert result is not None


def test_case_insensitive_blocking():
    result = server.validate_sql("drop TABLE daily_metrics")
    assert result is not None
