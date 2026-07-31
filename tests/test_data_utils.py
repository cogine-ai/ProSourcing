import pytest

from api.data_utils import (
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
        ({"category_stats": {"valid_product_qty": "8"}}, 8),
        ({"category_stats": '{"valid_product_count": "1,234"}'}, 1234),
        ({"category_stats": '{"valid_product_count": "bad"}'}, 0),
        ({"category_stats": {"valid_product_count": None, "valid_product_qty": 3}}, 3),
    ],
)
def test_get_task_valid_product_count(task, expected):
    assert get_task_valid_product_count(task) == expected


@pytest.mark.parametrize(
    "category_id,expected",
    [
        (None, ""),
        ("  ", ""),
        ("2466", "02466"),
        ("ABC12", "ABC12"),
    ],
)
def test_normalize_category_code(category_id, expected):
    assert normalize_category_code(category_id) == expected


def test_category_code_variants_deduplicates_numeric_aliases():
    assert category_code_variants("2466") == ["2466", "02466"]
    assert category_code_variants("02466") == ["02466", "2466"]
    assert category_code_variants("") == []
