"""Regression tests for pure task-history helpers in api.server."""

import json
from datetime import datetime

import pytest

from api.server import (
    _category_code_variants,
    _expand_status_filters,
    _extract_category_aliases,
    _get_task_valid_product_count,
    _normalize_category_code,
    _normalize_up_categories,
    _parse_task_timestamp,
    _task_matches_status_filters,
)


class TestGetTaskValidProductCount:
    def test_reads_valid_product_count(self):
        task = {"category_stats": {"valid_product_count": 42}}
        assert _get_task_valid_product_count(task) == 42

    def test_prefers_valid_product_count_over_qty(self):
        task = {"category_stats": {"valid_product_count": 10, "valid_product_qty": 20}}
        assert _get_task_valid_product_count(task) == 10

    def test_falls_back_to_valid_product_qty(self):
        task = {"category_stats": {"valid_product_qty": 15}}
        assert _get_task_valid_product_count(task) == 15

    def test_parses_json_string_stats(self):
        task = {"category_stats": json.dumps({"valid_product_count": 7})}
        assert _get_task_valid_product_count(task) == 7

    def test_parses_comma_formatted_numbers(self):
        task = {"category_stats": {"valid_product_count": "1,234"}}
        assert _get_task_valid_product_count(task) == 1234

    def test_strips_whitespace_values(self):
        task = {"category_stats": {"valid_product_count": "  88  "}}
        assert _get_task_valid_product_count(task) == 88

    def test_invalid_json_string_returns_zero(self):
        task = {"category_stats": "not-json"}
        assert _get_task_valid_product_count(task) == 0

    def test_invalid_numeric_value_skips_to_next_key(self):
        task = {"category_stats": {"valid_product_count": "n/a", "valid_product_qty": "5"}}
        assert _get_task_valid_product_count(task) == 5

    def test_missing_stats_returns_zero(self):
        assert _get_task_valid_product_count({}) == 0
        assert _get_task_valid_product_count({"category_stats": {}}) == 0
        assert _get_task_valid_product_count({"category_stats": None}) == 0


class TestNormalizeCategoryCode:
  @pytest.mark.parametrize(
      ("raw", "expected"),
      [
          ("123", "00123"),
          ("00123", "00123"),
          ("abc", "abc"),
          ("", ""),
          (None, ""),
      ],
  )
  def test_normalizes_codes(self, raw, expected):
      assert _normalize_category_code(raw) == expected


class TestCategoryCodeVariants:
    def test_generates_unique_variants(self):
        assert _category_code_variants("123") == ["123", "00123"]
        assert _category_code_variants("00123") == ["00123", "123"]
        assert _category_code_variants("") == []


class TestExtractCategoryAliases:
    def test_extracts_parenthetical_alias(self):
        aliases = _extract_category_aliases("Phones (Телефоны)")
        assert "Phones" in aliases
        assert "Телефоны" in aliases

    def test_extracts_dict_fields(self):
        aliases = _extract_category_aliases(
            {"category_name": "RPA采集_手机", "name_cn": "手机", "name_ru": "Телефоны"}
        )
        assert "手机" in aliases
        assert "Телефоны" in aliases


class TestNormalizeUpCategories:
    def test_parses_json_string_list(self):
        payload = json.dumps([{"category_name": "手机"}])
        assert _normalize_up_categories(payload) == [{"category_name": "手机"}]

    def test_wraps_plain_string(self):
        assert _normalize_up_categories("手机") == ["手机"]

    def test_returns_empty_for_blank_string(self):
        assert _normalize_up_categories("   ") == []


class TestExpandStatusFilters:
    def test_pending_expands_to_running_statuses(self):
        expanded = _expand_status_filters(["pending"])
        assert "scraping" in expanded
        assert "crawling" in expanded
        assert "processing" in expanded

    def test_all_is_ignored(self):
        assert _expand_status_filters(["all"]) == []

    def test_completed_passes_through(self):
        assert _expand_status_filters(["completed"]) == ["completed"]


class TestParseTaskTimestamp:
    def test_parses_iso_with_z_suffix(self):
        parsed = _parse_task_timestamp("2026-01-15T10:00:00Z")
        assert parsed == datetime.fromisoformat("2026-01-15T10:00:00+00:00")

    def test_invalid_timestamp_returns_none(self):
        assert _parse_task_timestamp("not-a-date") is None
        assert _parse_task_timestamp("") is None


class TestTaskMatchesStatusFilters:
    def test_empty_filter_matches_everything(self):
        assert _task_matches_status_filters({"status": "completed"}, []) is True

    def test_matches_case_insensitive(self):
        assert _task_matches_status_filters({"status": "Completed"}, ["completed"]) is True
