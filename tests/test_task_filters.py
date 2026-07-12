import pytest
from datetime import datetime

from api.task_filters import (
    apply_top_category_overrides,
    category_code_variants,
    contains_chinese,
    enrich_task_display_fields,
    expand_status_filters,
    extract_category_aliases,
    filter_tasks_with_valid_products,
    get_task_valid_product_count,
    normalize_category_code,
    normalize_up_categories,
    parse_task_timestamp,
    task_matches_days,
    task_matches_status_filters,
    task_matches_top_category,
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


@pytest.mark.parametrize(
    "category_id,expected",
    [
        ("246", ["246", "00246"]),
        ("00246", ["00246", "246"]),
        ("abc", ["abc"]),
        ("", []),
        ("00000", ["00000", "0"]),
    ],
)
def test_category_code_variants(category_id, expected):
    assert category_code_variants(category_id) == expected


@pytest.mark.parametrize(
    "value,expected_aliases",
    [
        (None, set()),
        ("", set()),
        ("Phones (手机)", {"Phones (手机)", "Phones", "手机"}),
        (
            {"category_name": "Drones (无人机)", "name_ru": "Drones"},
            {"Drones (无人机)", "Drones", "无人机"},
        ),
    ],
)
def test_extract_category_aliases(value, expected_aliases):
    assert extract_category_aliases(value) == expected_aliases


@pytest.mark.parametrize(
    "text,expected",
    [
        ("手机", True),
        ("Phones", False),
        ("Телефоны", False),
        ("", False),
        (None, False),
    ],
)
def test_contains_chinese(text, expected):
    assert contains_chinese(text) == expected


@pytest.mark.parametrize(
    "up_categories,expected",
    [
        (None, []),
        ("", []),
        ([{"name_cn": "手机"}], [{"name_cn": "手机"}]),
        ('[{"name_cn": "配件"}]', [{"name_cn": "配件"}]),
        ('{"name_cn": "无人机"}', [{"name_cn": "无人机"}]),
        ("Phones (手机)", ["Phones (手机)"]),
        ("not-json", ["not-json"]),
    ],
)
def test_normalize_up_categories(up_categories, expected):
    assert normalize_up_categories(up_categories) == expected


def test_task_matches_top_category_uses_aliases_and_json_path():
    task = {
        "up_categories": '[{"category_name": "Phones (手机)"}]',
    }
    assert task_matches_top_category(task, "手机") is True
    assert task_matches_top_category(task, "家电") is False
    assert task_matches_top_category(task, "") is True


def test_task_matches_top_category_falls_back_to_resolver():
    task = {"up_categories": None}

    def resolve(task):
        return [{"name_cn": "无人机"}]

    assert task_matches_top_category(task, "无人机", resolve_task_path=resolve) is True
    assert task_matches_top_category(task, "手机", resolve_task_path=resolve) is False


@pytest.mark.parametrize(
    "value,expected_parts",
    [
        (None, None),
        ("", None),
        ("2026-05-30T10:00:00", (2026, 5, 30, 10, 0, 0)),
        ("2026-05-30T10:00:00Z", (2026, 5, 30, 10, 0, 0)),
        ("not-a-date", None),
    ],
)
def test_parse_task_timestamp(value, expected_parts):
    result = parse_task_timestamp(value)
    if expected_parts is None:
        assert result is None
    else:
        assert (result.year, result.month, result.day, result.hour, result.minute, result.second) == expected_parts


def test_task_matches_days_uses_injected_now():
    fixed_now = datetime(2026, 5, 30, 12, 0, 0)
    recent = {"created_at": "2026-05-28T10:00:00"}
    old = {"created_at": "2026-01-01T10:00:00"}

    assert task_matches_days(recent, 7, now=fixed_now) is True
    assert task_matches_days(old, 7, now=fixed_now) is False
    assert task_matches_days(old, 0, now=fixed_now) is True
    assert task_matches_days({"created_at": "bad"}, 7, now=fixed_now) is False


@pytest.mark.parametrize(
    "task,expanded,expected",
    [
        ({"status": "Completed"}, ["completed"], True),
        ({"status": "failed"}, ["completed"], False),
        ({"status": "pending"}, [], True),
    ],
)
def test_task_matches_status_filters(task, expanded, expected):
    assert task_matches_status_filters(task, expanded) is expected


def test_apply_top_category_overrides_only_sets_provided_fields():
    payload = {"category": "Phones", "top_category_id": "1"}
    result = apply_top_category_overrides(
        payload,
        top_category_id="99",
        top_category_name_cn="手机",
    )
    assert result["top_category_id"] == "99"
    assert result["top_category_name_cn"] == "手机"
    assert "top_category_name_ru" not in result


def test_apply_top_category_overrides_coerces_values_to_strings():
    payload = {}
    apply_top_category_overrides(payload, top_category_id=246, top_category_name_ru="Телефоны")
    assert payload["top_category_id"] == "246"
    assert payload["top_category_name_ru"] == "Телефоны"


def test_enrich_task_display_fields_sets_top_label_and_leaf_category():
    task = {"category": "Phones"}
    task_path = [
        {"name_cn": "手机", "name_ru": "Phones"},
        {"name_cn": "配件", "category_name": "Accessories"},
    ]
    enrich_task_display_fields(task, task_path)
    assert task["top_category_label"] == "手机"
    assert task["category"] == "配件"
    assert task["up_categories"] == task_path


def test_enrich_task_display_fields_keeps_chinese_category():
    task = {"category": "无人机"}
    task_path = [{"name_cn": "数码"}, {"name_cn": "无人机"}]
    enrich_task_display_fields(task, task_path)
    assert task["category"] == "无人机"


def test_enrich_task_display_fields_handles_empty_path():
    task = {"category": "Phones"}
    enrich_task_display_fields(task, [])
    assert task["top_category_label"] is None
    assert task["category"] == "Phones"
