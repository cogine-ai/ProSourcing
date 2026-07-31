"""Pure helpers for task history filtering (stdlib-only for easy unit tests)."""
import json


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


def normalize_category_code(category_id):
    raw = str(category_id or "").strip()
    if not raw:
        return ""
    return raw.zfill(5) if raw.isdigit() else raw
