"""Pure helpers for task history filtering (stdlib-only for unit tests)."""

import json
from datetime import datetime, timedelta
from typing import Sequence

RUNNING_TASK_STATUSES = (
    "pending",
    "scraping",
    "crawling",
    "reporting",
    "processing",
    "retrying",
)


def get_task_valid_product_count(task):
    stats = task.get("category_stats") or {}
    if isinstance(stats, str):
        try:
            stats = json.loads(stats)
        except json.JSONDecodeError:
            stats = {}

    for key in ("valid_product_count", "valid_product_qty"):
        value = stats.get(key)
        if value is None:
            continue
        try:
            return int(float(str(value).replace(",", "").strip() or 0))
        except (TypeError, ValueError):
            continue

    return 0


def filter_tasks_with_valid_products(tasks):
    """Tasks kept when hide_zero is enabled (valid product count > 0)."""
    return [t for t in tasks if get_task_valid_product_count(t) > 0]


def expand_status_filters(status_filters):
    if not status_filters:
        return []

    if isinstance(status_filters, str):
        raw_filters = [status_filters]
    else:
        raw_filters = list(status_filters)

    expanded = []
    for item in raw_filters:
        normalized = (item or "").strip().lower()
        if not normalized or normalized == "all":
            continue
        if normalized == "pending":
            for running_status in RUNNING_TASK_STATUSES:
                if running_status not in expanded:
                    expanded.append(running_status)
            continue
        if normalized not in expanded:
            expanded.append(normalized)
    return expanded


def normalize_category_code(category_id):
    raw = str(category_id or "").strip()
    if not raw:
        return ""
    return raw.zfill(5) if raw.isdigit() else raw


def category_code_variants(category_id):
    raw = str(category_id or "").strip()
    if not raw:
        return []

    variants = []
    for candidate in (raw, raw.zfill(5) if raw.isdigit() else raw, raw.lstrip("0") or "0"):
        candidate = str(candidate).strip()
        if candidate and candidate not in variants:
            variants.append(candidate)
    return variants


def contains_chinese(text):
    return any("\u4e00" <= ch <= "\u9fff" for ch in str(text or ""))


def normalize_up_categories(up_categories):
    if not up_categories:
        return []

    if isinstance(up_categories, str):
        raw = up_categories.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            if parsed:
                return [parsed]
        except json.JSONDecodeError:
            return [raw]

    if isinstance(up_categories, list):
        return up_categories

    return [up_categories]


def apply_leaf_category_cn_label(task, task_path):
    """Replace non-Chinese leaf category labels with resolved Chinese names."""
    raw_category = str(task.get("category") or "").strip()
    leaf_category = task_path[-1] if task_path else None
    leaf_name_cn = str(
        (leaf_category or {}).get("name_cn") or (leaf_category or {}).get("category_name") or ""
    ).strip()
    if leaf_name_cn and (not raw_category or not contains_chinese(raw_category)):
        task["category"] = leaf_name_cn
    return task


def parse_task_timestamp(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def task_matches_days(task, days):
    if not days or days <= 0:
        return True
    created_at = parse_task_timestamp(task.get("created_at"))
    if not created_at:
        return False
    return created_at >= (datetime.now(created_at.tzinfo) - timedelta(days=days))


def task_matches_status_filters(task, expanded_statuses: Sequence[str]) -> bool:
    if not expanded_statuses:
        return True
    return (task.get("status") or "").strip().lower() in expanded_statuses
