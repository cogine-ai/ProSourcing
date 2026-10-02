from datetime import datetime


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


def norm_category_id_for_dedup(category_id):
    raw = str(category_id or "").strip()
    if not raw:
        return ""
    normalized = raw.lstrip("0")
    return normalized if normalized else "0"


def task_category_dedup_key(task):
    if not task:
        return ""
    return norm_category_id_for_dedup(task.get("category_id") or task.get("category"))


def select_tasks_for_recovery_requeue(matched_tasks, stale_before, all_in_flight_tasks):
    """Pick at most one stale task per category and skip categories with a fresh in-flight task."""
    fresh_categories = set()
    for task in all_in_flight_tasks or []:
        activity_time = parse_task_timestamp(task.get("updated_at")) or parse_task_timestamp(task.get("created_at"))
        if activity_time and activity_time > stale_before:
            dedup_key = task_category_dedup_key(task)
            if dedup_key:
                fresh_categories.add(dedup_key)

    selected = []
    enqueued_categories = set()
    for task in matched_tasks or []:
        dedup_key = task_category_dedup_key(task)
        if not dedup_key or dedup_key in fresh_categories or dedup_key in enqueued_categories:
            continue
        enqueued_categories.add(dedup_key)
        selected.append(task)
    return selected
