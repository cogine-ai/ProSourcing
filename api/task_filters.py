"""Pure helpers for task history filtering (stdlib-only, no FastAPI deps)."""

import json
from typing import Any, Dict, List


def get_task_valid_product_count(task: Dict[str, Any]) -> int:
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


def filter_tasks_with_products(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return tasks whose valid product count is strictly greater than zero."""
    return [task for task in tasks if get_task_valid_product_count(task) > 0]
