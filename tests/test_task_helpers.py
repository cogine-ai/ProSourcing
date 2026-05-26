from datetime import datetime, timedelta, timezone

import pytest

from api.task_helpers import (
    category_code_variants,
    expand_status_filters,
    get_task_valid_product_count,
    normalize_category_code,
    parse_task_timestamp,
    task_matches_days,
    task_matches_status_filters,
)


@pytest.mark.parametrize(
    "task,expected",
    [
        ({}, 0),
        ({"category_stats": None}, 0),
        ({"category_stats": {"valid_product_count": 12}}, 12),
        ({"category_stats": {"valid_product_qty": "3,500"}}, 3500),
        ({"category_stats": '{"valid_product_count": 7}'}, 7),
        ({"category_stats": '{"valid_product_count": broken}'}, 0),
        ({"category_stats": {"valid_product_count": "  ", "valid_product_qty": "9"}}, 0),
        ({"category_stats": {"valid_product_count": "n/a", "valid_product_qty": 4}}, 4),
    ],
)
def test_get_task_valid_product_count(task, expected):
    assert get_task_valid_product_count(task) == expected


@pytest.mark.parametrize(
    "category_id,expected",
    [
        ("", ""),
        ("  ", ""),
        ("1466", "01466"),
        ("01466", "01466"),
        ("ABC", "ABC"),
    ],
)
def test_normalize_category_code(category_id, expected):
    assert normalize_category_code(category_id) == expected


def test_category_code_variants_dedupes_and_preserves_order():
    assert category_code_variants("1466") == ["1466", "01466"]
    assert category_code_variants("") == []


def test_expand_status_filters_expands_pending_to_running_statuses():
    expanded = expand_status_filters(["pending"])
    assert "scraping" in expanded
    assert "completed" not in expanded


def test_expand_status_filters_skips_all_and_empty_tokens():
    assert expand_status_filters(["all", "", "completed"]) == ["completed"]


def test_expand_status_filters_deduplicates_values():
    assert expand_status_filters(["completed", "completed"]) == ["completed"]


def test_parse_task_timestamp_parses_iso_z_suffix():
    parsed = parse_task_timestamp("2026-01-15T10:00:00Z")
    assert parsed == datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


def test_parse_task_timestamp_returns_none_for_invalid_values():
    assert parse_task_timestamp("not-a-date") is None
    assert parse_task_timestamp("") is None


def test_task_matches_days_filters_by_recency():
    recent = {"created_at": (datetime.now() - timedelta(days=1)).isoformat()}
    old = {"created_at": (datetime.now() - timedelta(days=30)).isoformat()}
    assert task_matches_days(recent, 7) is True
    assert task_matches_days(old, 7) is False
    assert task_matches_days(old, None) is True


def test_task_matches_status_filters_case_insensitive():
    task = {"status": "Completed"}
    assert task_matches_status_filters(task, ["completed"]) is True
    assert task_matches_status_filters(task, ["failed"]) is False
    assert task_matches_status_filters({"status": "failed"}, []) is True
