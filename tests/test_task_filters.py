import pytest

from api.task_filters import (
    expand_status_filters,
    filter_tasks_with_valid_products,
    get_task_valid_product_count,
    normalize_category_code,
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
        ({"category_stats": {"valid_product_count": 42, "valid_product_qty": 99}}, 42),
    ],
)
def test_get_task_valid_product_count(task, expected):
    assert get_task_valid_product_count(task) == expected


def test_filter_tasks_with_valid_products_excludes_zero_counts():
    tasks = [
        {"id": "a", "category_stats": {"valid_product_count": 0}},
        {"id": "b", "category_stats": {"valid_product_qty": 3}},
        {"id": "c", "category_stats": {}},
        {"id": "d", "category_stats": {"valid_product_count": "2"}},
    ]
    filtered = filter_tasks_with_valid_products(tasks)
    assert [task["id"] for task in filtered] == ["b", "d"]


@pytest.mark.parametrize(
    "status_filters,expected",
    [
        (None, []),
        ([], []),
        (["all"], []),
        (["completed"], ["completed"]),
        (["Completed"], ["completed"]),
        (
            ["pending"],
            [
                "crawling",
                "pending",
                "processing",
                "reporting",
                "retrying",
                "scraping",
            ],
        ),
        (["pending", "failed"], ["crawling", "pending", "processing", "reporting", "retrying", "scraping", "failed"]),
        ("pending", ["crawling", "pending", "processing", "reporting", "retrying", "scraping"]),
        (["", "  all  ", "completed"], ["completed"]),
    ],
)
def test_expand_status_filters(status_filters, expected):
    assert expand_status_filters(status_filters) == expected


@pytest.mark.parametrize(
    "category_id,expected",
    [
        ("246", "00246"),
        (" 00002 ", "00002"),
        ("abc", "abc"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize_category_code(category_id, expected):
    assert normalize_category_code(category_id) == expected
