import pytest

from api.task_filters import (
    filter_tasks_with_valid_products,
    get_task_valid_product_count,
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
