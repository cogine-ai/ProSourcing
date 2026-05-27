from api.task_stats import get_task_valid_product_count


def test_valid_product_count_from_dict():
    task = {"category_stats": {"valid_product_count": 42}}
    assert get_task_valid_product_count(task) == 42


def test_valid_product_count_prefers_valid_product_count_over_qty():
    task = {
        "category_stats": {
            "valid_product_count": 10,
            "valid_product_qty": 99,
        }
    }
    assert get_task_valid_product_count(task) == 10


def test_valid_product_count_parses_json_string_stats():
    task = {"category_stats": '{"valid_product_qty": "1,234"}'}
    assert get_task_valid_product_count(task) == 1234


def test_valid_product_count_falls_back_to_valid_product_qty():
    task = {"category_stats": {"valid_product_qty": "56"}}
    assert get_task_valid_product_count(task) == 56


def test_valid_product_count_invalid_json_string_returns_zero():
    task = {"category_stats": "not-json"}
    assert get_task_valid_product_count(task) == 0


def test_valid_product_count_skips_unparseable_values():
    task = {"category_stats": {"valid_product_count": "n/a", "valid_product_qty": 7}}
    assert get_task_valid_product_count(task) == 7


def test_valid_product_count_missing_stats_returns_zero():
    assert get_task_valid_product_count({}) == 0
    assert get_task_valid_product_count({"category_stats": None}) == 0
