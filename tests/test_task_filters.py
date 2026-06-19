from datetime import datetime, timedelta, timezone

import pytest

from api.task_filters import (
    expand_status_filters,
    filter_tasks_with_valid_products,
    get_task_valid_product_count,
    normalize_category_code,
    parse_task_timestamp,
    task_matches_days,
    task_matches_status_filters,
)


class TestGetTaskValidProductCount:
    def test_reads_valid_product_count_from_dict_stats(self):
        task = {"category_stats": {"valid_product_count": 12}}
        assert get_task_valid_product_count(task) == 12

    def test_prefers_valid_product_count_over_qty(self):
        task = {
            "category_stats": {
                "valid_product_count": 3,
                "valid_product_qty": 99,
            }
        }
        assert get_task_valid_product_count(task) == 3

    def test_parses_json_string_stats(self):
        task = {"category_stats": '{"valid_product_qty": 7}'}
        assert get_task_valid_product_count(task) == 7

    def test_strips_commas_and_whitespace(self):
        task = {"category_stats": {"valid_product_count": " 1,234 "}}
        assert get_task_valid_product_count(task) == 1234

    def test_falls_back_to_valid_product_qty(self):
        task = {"category_stats": {"valid_product_qty": "42"}}
        assert get_task_valid_product_count(task) == 42

    def test_returns_zero_for_invalid_stats(self):
        assert get_task_valid_product_count({}) == 0
        assert get_task_valid_product_count({"category_stats": "not-json"}) == 0
        assert get_task_valid_product_count({"category_stats": {"valid_product_count": "n/a"}}) == 0


class TestNormalizeCategoryCode:
    def test_zero_pads_numeric_codes(self):
        assert normalize_category_code("1466") == "01466"
        assert normalize_category_code(2) == "00002"

    def test_preserves_non_numeric_codes(self):
        assert normalize_category_code("abc") == "abc"

    def test_empty_input(self):
        assert normalize_category_code("") == ""
        assert normalize_category_code(None) == ""


class TestFilterTasksWithValidProducts:
    def test_keeps_only_tasks_with_positive_valid_count(self):
        tasks = [
            {"id": "a", "category_stats": {"valid_product_count": 0}},
            {"id": "b", "category_stats": {"valid_product_count": 3}},
            {"id": "c", "category_stats": {}},
        ]
        kept = filter_tasks_with_valid_products(tasks)
        assert [t["id"] for t in kept] == ["b"]


class TestExpandStatusFilters:
    def test_expands_pending_to_running_statuses(self):
        expanded = expand_status_filters(["pending"])
        assert "scraping" in expanded
        assert "completed" not in expanded

    def test_skips_all_and_empty_tokens(self):
        assert expand_status_filters(["all", "", "completed"]) == ["completed"]

    def test_deduplicates_values(self):
        assert expand_status_filters(["completed", "completed"]) == ["completed"]


class TestParseTaskTimestamp:
    def test_parses_iso_z_suffix(self):
        parsed = parse_task_timestamp("2026-01-15T10:00:00Z")
        assert parsed == datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    def test_returns_none_for_invalid_values(self):
        assert parse_task_timestamp("not-a-date") is None
        assert parse_task_timestamp("") is None


class TestTaskMatchesDays:
    def test_matches_recent_tasks_only(self):
        recent = {
            "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
        }
        old = {
            "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
        }
        assert task_matches_days(recent, 7) is True
        assert task_matches_days(old, 7) is False
        assert task_matches_days(old, None) is True


class TestTaskMatchesStatusFilters:
    def test_matches_case_insensitive_status(self):
        task = {"status": "Completed"}
        assert task_matches_status_filters(task, ["completed"]) is True
        assert task_matches_status_filters(task, ["failed"]) is False

    def test_empty_filter_matches_everything(self):
        assert task_matches_status_filters({"status": "failed"}, []) is True
