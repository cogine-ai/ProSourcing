"""Pure helpers for task history filtering (stdlib-only for unit tests)."""

import json

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


def filter_tasks_with_valid_products(tasks):
    """Tasks kept when hide_zero is enabled (valid product count > 0)."""
    return [t for t in tasks if get_task_valid_product_count(t) > 0]
