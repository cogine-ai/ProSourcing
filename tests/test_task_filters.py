import json
from datetime import datetime, timedelta

import pytest

from api.task_filters import (
    apply_top_category_overrides,
    category_code_variants,
    contains_chinese,
    expand_status_filters,
    extract_category_aliases,
    filter_tasks_with_valid_products,
    get_task_valid_product_count,
    normalize_category_code,
    normalize_up_categories,
    parse_task_timestamp,
    task_matches_days,
    task_matches_status_filters,
    task_matches_top_category,
)


class TestGetTaskValidProductCount:
    def test_reads_valid_product_count(self):
        task = {"category_stats": {"valid_product_count": 12}}
        assert get_task_valid_product_count(task) == 12

    def test_falls_back_to_valid_product_qty(self):
        task = {"category_stats": {"valid_product_qty": "8"}}
        assert get_task_valid_product_count(task) == 8

    def test_parses_json_string_stats(self):
        task = {"category_stats": json.dumps({"valid_product_count": "1,234"})}
        assert get_task_valid_product_count(task) == 1234

    def test_invalid_stats_return_zero(self):
        task = {"category_stats": {"valid_product_count": "n/a"}}
        assert get_task_valid_product_count(task) == 0

    def test_missing_stats_return_zero(self):
        assert get_task_valid_product_count({}) == 0


class TestFilterTasksWithValidProducts:
    def test_filters_zero_count_tasks(self):
        tasks = [
            {"id": "a", "category_stats": {"valid_product_count": 0}},
            {"id": "b", "category_stats": {"valid_product_count": 3}},
            {"id": "c", "category_stats": {}},
        ]
        filtered = filter_tasks_with_valid_products(tasks)
        assert [task["id"] for task in filtered] == ["b"]


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
        assert normalize_category_code(raw) == expected


class TestCategoryCodeVariants:
    def test_generates_unique_variants(self):
        assert category_code_variants("123") == ["123", "00123"]
        assert category_code_variants("00123") == ["00123", "123"]

    def test_empty_input(self):
        assert category_code_variants("") == []


class TestExtractCategoryAliases:
    def test_parses_parenthetical_name(self):
        aliases = extract_category_aliases("Phones (手机)")
        assert aliases == {"Phones (手机)", "Phones", "手机"}

    def test_collects_dict_fields(self):
        aliases = extract_category_aliases(
            {"category_name": "TVs", "name_cn": "电视", "name_ru": "Телевизоры"}
        )
        assert "TVs" in aliases
        assert "电视" in aliases
        assert "Телевизоры" in aliases


class TestContainsChinese:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("手机", True),
            ("Phones", False),
            ("Phones (手机)", True),
            ("", False),
            (None, False),
        ],
    )
    def test_detects_chinese(self, text, expected):
        assert contains_chinese(text) is expected


class TestNormalizeUpCategories:
    def test_parses_json_array_string(self):
        payload = json.dumps([{"category_name": "A"}, {"category_name": "B"}])
        assert normalize_up_categories(payload) == [{"category_name": "A"}, {"category_name": "B"}]

    def test_wraps_plain_string(self):
        assert normalize_up_categories("Electronics") == ["Electronics"]

    def test_invalid_json_becomes_single_item_list(self):
        assert normalize_up_categories("not-json") == ["not-json"]

    def test_empty_values(self):
        assert normalize_up_categories(None) == []
        assert normalize_up_categories("") == []
        assert normalize_up_categories("   ") == []


class TestTaskMatchesTopCategory:
    def test_matches_alias_in_path(self):
        task = {
            "up_categories": [
                {"category_name": "Phones (手机)"},
                {"category_name": "Smartphones"},
            ]
        }
        assert task_matches_top_category(task, "手机") is True

    def test_no_match(self):
        task = {"up_categories": [{"category_name": "TVs"}]}
        assert task_matches_top_category(task, "手机") is False

    def test_empty_filter_matches_all(self):
        task = {"up_categories": [{"category_name": "TVs"}]}
        assert task_matches_top_category(task, "") is True

    def test_uses_resolver_when_path_missing(self):
        task = {"category_id": "00001"}

        def resolver(_task):
            return [{"category_name": "Resolved Category"}]

        assert task_matches_top_category(task, "Resolved Category", resolver) is True


class TestExpandStatusFilters:
    def test_expands_pending_to_running_statuses(self):
        expanded = expand_status_filters(["pending"])
        assert "pending" in expanded
        assert "scraping" in expanded
        assert "processing" in expanded

    def test_skips_all_and_blank(self):
        assert expand_status_filters(["all", "", "completed"]) == ["completed"]

    def test_deduplicates(self):
        assert expand_status_filters(["completed", "completed"]) == ["completed"]


class TestParseTaskTimestamp:
    def test_parses_iso_string(self):
        parsed = parse_task_timestamp("2026-04-10T12:30:00")
        assert parsed == datetime(2026, 4, 10, 12, 30, 0)

    def test_parses_zulu_suffix(self):
        parsed = parse_task_timestamp("2026-04-10T12:30:00Z")
        assert parsed == datetime.fromisoformat("2026-04-10T12:30:00+00:00")

    def test_invalid_values_return_none(self):
        assert parse_task_timestamp("") is None
        assert parse_task_timestamp("not-a-date") is None


class TestTaskMatchesDays:
    def test_recent_task_matches(self):
        task = {"created_at": datetime.now().isoformat()}
        assert task_matches_days(task, 7) is True

    def test_old_task_does_not_match(self):
        old = datetime.now() - timedelta(days=30)
        task = {"created_at": old.isoformat()}
        assert task_matches_days(task, 7) is False

    def test_non_positive_days_matches_all(self):
        task = {"created_at": "2020-01-01T00:00:00"}
        assert task_matches_days(task, 0) is True


class TestTaskMatchesStatusFilters:
    def test_matches_status_case_insensitively(self):
        task = {"status": "Completed"}
        assert task_matches_status_filters(task, ["completed"]) is True

    def test_empty_filter_matches_all(self):
        assert task_matches_status_filters({"status": "failed"}, []) is True


class TestApplyTopCategoryOverrides:
    def test_applies_only_provided_fields(self):
        payload = {"category": "Phones"}
        result = apply_top_category_overrides(
            payload,
            top_category_id="00002",
            top_category_name_cn="手机",
        )
        assert result["top_category_id"] == "00002"
        assert result["top_category_name_cn"] == "手机"
        assert "top_category_name_ru" not in result
