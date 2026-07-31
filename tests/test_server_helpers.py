import json
import sys
from unittest.mock import MagicMock

import pytest

# Keep Supabase and pipeline side effects out of helper unit tests.
_mock_pipeline = MagicMock()
_mock_pipeline.run_scoring_and_export = MagicMock()
_mock_pipeline.supabase = MagicMock()
sys.modules["core.final_pipeline"] = _mock_pipeline

_mock_scoring = MagicMock()
_mock_scoring.ScoringEngine = MagicMock()
_mock_scoring.DEFAULT_CONFIG = {}
sys.modules["core.scoring"] = _mock_scoring

from api import server


@pytest.fixture(autouse=True)
def clear_category_cache():
    server._get_category_master_row.cache_clear()
    yield
    server._get_category_master_row.cache_clear()


class TestGetTaskValidProductCount:
    def test_reads_numeric_fields_with_comma_formatting(self):
        task = {"category_stats": {"valid_product_count": "1,234"}}
        assert server._get_task_valid_product_count(task) == 1234

    def test_falls_back_to_valid_product_qty(self):
        task = {"category_stats": {"valid_product_qty": "42"}}
        assert server._get_task_valid_product_count(task) == 42

    def test_parses_json_encoded_stats(self):
        task = {"category_stats": json.dumps({"valid_product_count": 7})}
        assert server._get_task_valid_product_count(task) == 7

    def test_returns_zero_for_missing_or_invalid_stats(self):
        assert server._get_task_valid_product_count({}) == 0
        assert server._get_task_valid_product_count({"category_stats": "not-json"}) == 0
        assert server._get_task_valid_product_count({"category_stats": {"valid_product_count": "n/a"}}) == 0


class TestCategoryNormalizationHelpers:
    def test_normalize_category_code_zero_pads_digits(self):
        assert server._normalize_category_code("2466") == "02466"
        assert server._normalize_category_code("ABC") == "ABC"

    def test_contains_chinese(self):
        assert server._contains_chinese("手机") is True
        assert server._contains_chinese("Phones") is False
        assert server._contains_chinese(None) is False

    def test_normalize_up_categories_handles_json_strings(self):
        payload = json.dumps([{"category_name": "手机"}])
        assert server._normalize_up_categories(payload) == [{"category_name": "手机"}]

    def test_extract_category_aliases_expands_parenthetical_names(self):
        aliases = server._extract_category_aliases("Phones (手机)")
        assert {"Phones", "手机"}.issubset(aliases)


class TestExpandStatusFilters:
    def test_pending_expands_to_running_statuses(self):
        expanded = server._expand_status_filters(["pending"])
        assert "scraping" in expanded
        assert "processing" in expanded
        assert "completed" not in expanded

    def test_ignores_all_and_blank_filters(self):
        assert server._expand_status_filters(["all", "", "completed"]) == ["completed"]


class TestEnrichTaskMetadata:
    def test_backfills_leaf_chinese_category_when_raw_label_is_russian(self):
        task = {
            "category": "Телефоны",
            "up_categories": [
                {
                    "name_cn": "电子产品",
                    "category_name": "电子产品",
                    "name_ru": "Электроника",
                },
                {
                    "name_cn": "手机",
                    "category_name": "手机",
                    "name_ru": "Телефоны",
                },
            ],
        }

        server._enrich_task_metadata(task)

        assert task["category"] == "手机"
        assert task["top_category_label"] == "电子产品"

    def test_keeps_existing_chinese_category_label(self):
        task = {
            "category": "手机配件",
            "up_categories": [{"name_cn": "手机", "category_name": "手机"}],
        }

        server._enrich_task_metadata(task)

        assert task["category"] == "手机配件"

    def test_resolves_category_id_from_category_stats_when_task_field_missing(self, monkeypatch):
        lineage = {
            "00002": {
                "algatop_id": "00002",
                "parent_id": "00001",
                "name_ru": "Телефоны",
                "name_cn": "手机",
            },
            "00001": {
                "algatop_id": "00001",
                "parent_id": None,
                "name_ru": "Электроника",
                "name_cn": "电子产品",
            },
        }

        def fake_lookup(category_id):
            return lineage.get(str(category_id))

        monkeypatch.setattr(server, "_get_category_master_row", fake_lookup)

        task = {"category_stats": {"category_ext_id": "00002"}}
        server._enrich_task_metadata(task)

        assert [item["name_cn"] for item in task["up_categories"]] == ["电子产品", "手机"]
        assert task["top_category_label"] == "电子产品"


class TestTopCategoryStatsScriptPath:
    def test_points_to_fetch_top_category_stats_script(self):
        script_path, project_root = server._get_top_category_stats_script_path()
        assert script_path.endswith("core/fetch_top_category_stats.py")
        assert script_path.startswith(project_root)
