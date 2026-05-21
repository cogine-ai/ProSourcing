import pytest

from api.task_helpers import (
    category_code_variants,
    get_task_valid_product_count,
    normalize_category_code,
)


@pytest.mark.parametrize(
    "task,expected",
    [
        ({}, 0),
        ({"category_stats": None}, 0),
        ({"category_stats": {"valid_product_count": 12}}, 12),
        ({"category_stats": {"valid_product_qty": "3,500"}}, 3500),
        ({"category_stats": '{"valid_product_count": 7}'}, 7),
        ({"category_stats": '{"valid_product_count": broken}'}, 0),
        ({"category_stats": {"valid_product_count": "  ", "valid_product_qty": "9"}}, 0),
        ({"category_stats": {"valid_product_count": "n/a", "valid_product_qty": 4}}, 4),
    ],
)
def test_get_task_valid_product_count(task, expected):
    assert get_task_valid_product_count(task) == expected


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
