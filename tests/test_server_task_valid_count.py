import sys
from unittest.mock import MagicMock

# Stub heavy dependencies so we can import isolated server helpers.
sys.modules.setdefault("core.final_pipeline", MagicMock())
sys.modules.setdefault("core.scoring", MagicMock())

from api.server import _get_task_valid_product_count


def test_valid_product_count_from_dict_stats():
    task = {"category_stats": {"valid_product_count": 42}}
    assert _get_task_valid_product_count(task) == 42


def test_valid_product_count_prefers_valid_product_count_over_qty():
    task = {
        "category_stats": {
            "valid_product_count": 10,
            "valid_product_qty": 99,
        }
    }
    assert _get_task_valid_product_count(task) == 10


def test_valid_product_count_falls_back_to_valid_product_qty():
    task = {"category_stats": {"valid_product_qty": 7}}
    assert _get_task_valid_product_count(task) == 7


def test_valid_product_count_parses_json_string_stats():
    task = {"category_stats": '{"valid_product_count": 15}'}
    assert _get_task_valid_product_count(task) == 15


def test_valid_product_count_parses_comma_separated_numbers():
    task = {"category_stats": {"valid_product_count": "1,234"}}
    assert _get_task_valid_product_count(task) == 1234


def test_valid_product_count_handles_invalid_json_string():
    task = {"category_stats": "not-json"}
    assert _get_task_valid_product_count(task) == 0


def test_valid_product_count_handles_non_numeric_values():
    task = {"category_stats": {"valid_product_count": "n/a", "valid_product_qty": "bad"}}
    assert _get_task_valid_product_count(task) == 0


def test_valid_product_count_returns_zero_when_missing():
    assert _get_task_valid_product_count({}) == 0
    assert _get_task_valid_product_count({"category_stats": {}}) == 0
