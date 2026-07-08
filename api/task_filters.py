"""Pure task-filter helpers (stdlib-only) for history filtering and unit tests."""

import json

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
