import json

import pytest

from api.task_filters import (
    expand_status_filters,
    filter_tasks_with_valid_products,
    get_task_valid_product_count,
)


@pytest.mark.parametrize(
    "task,expected",
    [
        ({}, 0),
        ({"category_stats": None}, 0),
        ({"category_stats": {"valid_product_count": 12}}, 12),
        ({"category_stats": {"valid_product_count": 5, "valid_product_qty": 99}}, 5),
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
        ({"category_stats": {"valid_product_count": "n/a", "valid_product_qty": 7}}, 7),
    ],
)
def test_get_task_valid_product_count(task, expected):
    assert get_task_valid_product_count(task) == expected


def test_filter_tasks_with_valid_products():
    tasks = [
        {"id": "a", "category_stats": {"valid_product_count": 0}},
        {"id": "b", "category_stats": {"valid_product_count": 3}},
        {"id": "c", "category_stats": {}},
        {"id": "d", "category_stats": json.dumps({"valid_product_qty": 2})},
    ]
    kept = filter_tasks_with_valid_products(tasks)
    assert [t["id"] for t in kept] == ["b", "d"]


@pytest.mark.parametrize(
    "status_filters,expected",
    [
        (None, []),
        ([], []),
        (["all", "completed"], ["completed"]),
        (
            ["pending"],
            [
                "pending",
                "scraping",
                "crawling",
                "reporting",
                "processing",
                "retrying",
            ],
        ),
        (["Completed", " completed "], ["completed"]),
        ("failed", ["failed"]),
    ],
)
def test_expand_status_filters(status_filters, expected):
    assert expand_status_filters(status_filters) == expected
