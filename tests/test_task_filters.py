import json

from api.task_filters import (
    expand_status_filters,
    filter_tasks_with_valid_products,
    get_task_valid_product_count,
)


def test_valid_product_count_from_dict_stats():
    task = {"category_stats": {"valid_product_count": 12}}
    assert get_task_valid_product_count(task) == 12


def test_valid_product_count_prefers_valid_product_count_over_qty():
    task = {"category_stats": {"valid_product_count": 5, "valid_product_qty": 99}}
    assert get_task_valid_product_count(task) == 5


def test_valid_product_count_falls_back_to_valid_product_qty():
    task = {"category_stats": {"valid_product_qty": "42"}}
    assert get_task_valid_product_count(task) == 42


def test_valid_product_count_parses_json_string_stats():
    task = {"category_stats": json.dumps({"valid_product_count": "1,234"})}
    assert get_task_valid_product_count(task) == 1234


def test_valid_product_count_invalid_json_string_returns_zero():
    task = {"category_stats": "not-json"}
    assert get_task_valid_product_count(task) == 0


def test_valid_product_count_skips_unparseable_values():
    task = {"category_stats": {"valid_product_count": "n/a", "valid_product_qty": 7}}
    assert get_task_valid_product_count(task) == 7


def test_valid_product_count_missing_stats_is_zero():
    assert get_task_valid_product_count({}) == 0
    assert get_task_valid_product_count({"category_stats": None}) == 0


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
