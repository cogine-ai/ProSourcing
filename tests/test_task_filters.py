import json

from api.task_filters import filter_tasks_with_products, get_task_valid_product_count


def test_valid_product_count_from_dict_stats():
    task = {"category_stats": {"valid_product_count": 42}}
    assert get_task_valid_product_count(task) == 42


def test_valid_product_count_prefers_valid_product_count_over_qty():
    task = {"category_stats": {"valid_product_count": 10, "valid_product_qty": 99}}
    assert get_task_valid_product_count(task) == 10


def test_valid_product_count_falls_back_to_valid_product_qty():
    task = {"category_stats": {"valid_product_qty": "1,234"}}
    assert get_task_valid_product_count(task) == 1234


def test_valid_product_count_parses_json_string_stats():
    task = {"category_stats": json.dumps({"valid_product_count": "7"})}
    assert get_task_valid_product_count(task) == 7


def test_valid_product_count_returns_zero_for_missing_or_invalid_stats():
    assert get_task_valid_product_count({}) == 0
    assert get_task_valid_product_count({"category_stats": "not-json"}) == 0
    assert get_task_valid_product_count({"category_stats": {"valid_product_count": "n/a"}}) == 0
    assert get_task_valid_product_count({"category_stats": {"valid_product_count": None, "valid_product_qty": None}}) == 0


def test_filter_tasks_with_products_excludes_zero_count_tasks():
    tasks = [
        {"id": "a", "category_stats": {"valid_product_count": 5}},
        {"id": "b", "category_stats": {"valid_product_count": 0}},
        {"id": "c", "category_stats": {}},
        {"id": "d", "category_stats": {"valid_product_qty": 2}},
    ]
    filtered = filter_tasks_with_products(tasks)
    assert [t["id"] for t in filtered] == ["a", "d"]
