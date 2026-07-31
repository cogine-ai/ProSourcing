from api.task_filters import get_task_valid_product_count, normalize_category_code


def test_get_task_valid_product_count_prefers_valid_product_count():
    task = {"category_stats": {"valid_product_count": 42, "valid_product_qty": 99}}
    assert get_task_valid_product_count(task) == 42


def test_get_task_valid_product_count_falls_back_to_valid_product_qty():
    task = {"category_stats": {"valid_product_qty": "15"}}
    assert get_task_valid_product_count(task) == 15


def test_get_task_valid_product_count_parses_comma_separated_strings():
    task = {"category_stats": {"valid_product_count": "1,234"}}
    assert get_task_valid_product_count(task) == 1234


def test_get_task_valid_product_count_parses_json_string_stats():
    task = {"category_stats": '{"valid_product_count": 7}'}
    assert get_task_valid_product_count(task) == 7


def test_get_task_valid_product_count_returns_zero_for_invalid_stats():
    assert get_task_valid_product_count({}) == 0
    assert get_task_valid_product_count({"category_stats": "not-json"}) == 0
    assert get_task_valid_product_count({"category_stats": {"valid_product_count": "n/a"}}) == 0


def test_normalize_category_code_zero_pads_numeric_ids():
    assert normalize_category_code("246") == "00246"
    assert normalize_category_code(" 00002 ") == "00002"


def test_normalize_category_code_preserves_non_numeric_ids():
    assert normalize_category_code("abc") == "abc"
    assert normalize_category_code("") == ""
