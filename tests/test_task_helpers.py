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
        ({"category_stats": {}}, 0),
        ({"category_stats": {"valid_product_count": 12}}, 12),
        ({"category_stats": {"valid_product_qty": "2,500"}}, 2500),
        ({"category_stats": '{"valid_product_count": "99"}'}, 99),
        ({"category_stats": '{"valid_product_count": "bad"}'}, 0),
        (
            {
                "category_stats": {
                    "valid_product_count": "bad",
                    "valid_product_qty": "7",
                }
            },
            7,
        ),
    ],
)
def test_get_task_valid_product_count(task, expected):
    assert get_task_valid_product_count(task) == expected


@pytest.mark.parametrize(
    "category_id,expected",
    [
        ("", ""),
        ("1466", "01466"),
        ("01466", "01466"),
        ("ABC", "ABC"),
    ],
)
def test_normalize_category_code(category_id, expected):
    assert normalize_category_code(category_id) == expected


def test_category_code_variants_deduplicates_numeric_aliases():
    assert category_code_variants("1466") == ["1466", "01466"]
    assert category_code_variants("01466") == ["01466", "1466"]
    assert category_code_variants("") == []
