import sys
from unittest.mock import MagicMock

import pytest

# Import server helpers without pulling heavy pipeline dependencies.
if "core.final_pipeline" not in sys.modules:
    sys.modules["core.final_pipeline"] = MagicMock()

from api.server import (  # noqa: E402
    _category_code_variants,
    _get_task_valid_product_count,
    _normalize_category_code,
)


@pytest.mark.parametrize(
    ("category_id", "expected"),
    [
        ("1466", "01466"),
        ("01466", "01466"),
        ("abc", "abc"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize_category_code(category_id, expected):
    assert _normalize_category_code(category_id) == expected


def test_category_code_variants_include_zero_padded_and_trimmed():
    assert _category_code_variants("1466") == ["1466", "01466"]
    assert _category_code_variants("01466") == ["01466", "1466"]


@pytest.mark.parametrize(
    ("task", "expected"),
    [
        ({"category_stats": {"valid_product_count": 12}}, 12),
        ({"category_stats": {"valid_product_qty": "8"}}, 8),
        ({"category_stats": '{"valid_product_count": "1,234"}'}, 1234),
        ({"category_stats": {"valid_product_count": "bad", "valid_product_qty": "3"}}, 3),
        ({"category_stats": {}}, 0),
        ({}, 0),
    ],
)
def test_get_task_valid_product_count(task, expected):
    assert _get_task_valid_product_count(task) == expected


def test_get_task_valid_product_count_prefers_first_valid_key():
    task = {
        "category_stats": {
            "valid_product_count": "0",
            "valid_product_qty": "15",
        }
    }
    assert _get_task_valid_product_count(task) == 0
