"""Pure task-filter helpers (stdlib-only) for history filtering and unit tests."""

import json
from datetime import datetime, timedelta

RUNNING_TASK_STATUSES = frozenset(
    {"pending", "scraping", "crawling", "reporting", "processing", "retrying"}
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
    """Keep tasks that have at least one valid product (hide_zero semantics)."""
    return [task for task in tasks if get_task_valid_product_count(task) > 0]


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
            for running_status in sorted(RUNNING_TASK_STATUSES):
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


def extract_category_aliases(category_value):
    aliases = set()
    if category_value is None:
        return aliases

    if isinstance(category_value, str):
        value = category_value.strip()
        if not value:
            return aliases
        aliases.add(value)
        if " (" in value and value.endswith(")"):
            main_part, _, tail = value.partition(" (")
            aliases.add(main_part.strip())
            aliases.add(tail[:-1].strip())
        return {alias for alias in aliases if alias}

    if isinstance(category_value, dict):
        for key in ("category_name", "name_ru", "name_cn", "category_cn", "name"):
            value = category_value.get(key)
            if isinstance(value, str) and value.strip():
                aliases.update(extract_category_aliases(value))
        return aliases

    return aliases


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


def task_matches_top_category(task, top_category, resolve_task_path=None):
    target_aliases = extract_category_aliases(top_category)
    if not target_aliases:
        return True

    task_path = normalize_up_categories(task.get("up_categories"))
    if not task_path and resolve_task_path:
        task_path = resolve_task_path(task) or []

    for item in task_path:
        if extract_category_aliases(item) & target_aliases:
            return True

    return False


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


def task_matches_days(task, days, now=None):
    if not days or days <= 0:
        return True
    created_at = parse_task_timestamp(task.get("created_at"))
    if not created_at:
        return False
    reference = now or datetime.now(created_at.tzinfo)
    return created_at >= (reference - timedelta(days=days))


def task_matches_status_filters(task, expanded_statuses):
    if not expanded_statuses:
        return True
    return (task.get("status") or "").strip().lower() in expanded_statuses


def apply_top_category_overrides(
    payload,
    top_category_id=None,
    top_category_name_cn=None,
    top_category_name_ru=None,
):
    if top_category_id:
        payload["top_category_id"] = str(top_category_id)
    if top_category_name_cn:
        payload["top_category_name_cn"] = str(top_category_name_cn)
    if top_category_name_ru:
        payload["top_category_name_ru"] = str(top_category_name_ru)
    return payload


def enrich_task_display_fields(task, task_path):
    """Apply display metadata from a resolved up_categories path (pure helper)."""
    if task_path:
        task["up_categories"] = task_path
        top_category = task_path[0]
        task["top_category_label"] = (
            top_category.get("name_cn")
            or top_category.get("category_name")
            or top_category.get("name_ru")
            or "一级分类"
        )
    else:
        task["top_category_label"] = None

    raw_category = str(task.get("category") or "").strip()
    leaf_category = task_path[-1] if task_path else None
    leaf_name_cn = str(
        (leaf_category or {}).get("name_cn") or (leaf_category or {}).get("category_name") or ""
    ).strip()
    if leaf_name_cn and (not raw_category or not contains_chinese(raw_category)):
        task["category"] = leaf_name_cn

    return task
