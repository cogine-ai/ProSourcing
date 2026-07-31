import json
from datetime import datetime, timedelta, timezone

import pytest

from api.task_filters import (
    apply_leaf_category_cn_label,
    category_code_variants,
    contains_chinese,
    expand_status_filters,
    filter_tasks_with_valid_products,
    get_task_valid_product_count,
    normalize_category_code,
    normalize_up_categories,
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
        ({"category_stats": {"valid_product_qty": "1,234"}}, 1234),
        ({"category_stats": '{"valid_product_count": 7}'}, 7),
        ({"category_stats": '{"valid_product_qty": 3}'}, 3),
        ({"category_stats": '{"valid_product_count": "not-a-number"}'}, 0),
        ({"category_stats": "not-json"}, 0),
        (
            {"category_stats": {"valid_product_count": None, "valid_product_qty": 5}},
            5,
        ),
        ({"category_stats": {"valid_product_count": "  42.0  "}}, 42),
        ({"category_stats": {"valid_product_count": 5, "valid_product_qty": 99}}, 5),
    ],
)
def test_get_task_valid_product_count(task, expected):
    assert get_task_valid_product_count(task) == expected


def test_filter_tasks_with_valid_products():
    tasks = [
        {"id": "a", "category_stats": {"valid_product_count": 0}},
        {"id": "b", "category_stats": {"valid_product_count": 3}},
        {"id": "c", "category_stats": {}},
    ]
    kept = filter_tasks_with_valid_products(tasks)
    assert [t["id"] for t in kept] == ["b"]


def test_expand_status_filters_empty():
    assert expand_status_filters(None) == []
    assert expand_status_filters([]) == []


def test_expand_status_filters_ignores_all():
    assert expand_status_filters(["all", "completed"]) == ["completed"]


def test_expand_status_filters_expands_pending_to_running_set():
    expanded = expand_status_filters(["pending"])
    assert expanded == [
        "pending",
        "scraping",
        "crawling",
        "reporting",
        "processing",
        "retrying",
    ]


def test_expand_status_filters_deduplicates_and_normalizes():
    assert expand_status_filters(["Completed", " completed "]) == ["completed"]


def test_expand_status_filters_accepts_single_string():
    assert expand_status_filters("failed") == ["failed"]


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


@pytest.mark.parametrize(
    "value,expected",
    [
        ("手机配件", True),
        ("Phones", False),
        ("", False),
        (None, False),
    ],
)
def test_contains_chinese(value, expected):
    assert contains_chinese(value) is expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, []),
        ([{"name_cn": "手机"}], [{"name_cn": "手机"}]),
        ('[{"name_cn": "手机"}]', [{"name_cn": "手机"}]),
        ('{"name_cn": "手机"}', [{"name_cn": "手机"}]),
        ("手机", ["手机"]),
        ("not-json", ["not-json"]),
    ],
)
def test_normalize_up_categories(raw, expected):
    assert normalize_up_categories(raw) == expected


def test_apply_leaf_category_cn_label_replaces_non_chinese_category():
    task = {"category": "Phones"}
    task_path = [{"name_cn": "手机"}, {"name_cn": "手机壳", "category_name": "手机壳"}]
    apply_leaf_category_cn_label(task, task_path)
    assert task["category"] == "手机壳"


def test_apply_leaf_category_cn_label_keeps_existing_chinese_category():
    task = {"category": "已有中文品类"}
    task_path = [{"name_cn": "手机"}, {"name_cn": "手机壳"}]
    apply_leaf_category_cn_label(task, task_path)
    assert task["category"] == "已有中文品类"


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
