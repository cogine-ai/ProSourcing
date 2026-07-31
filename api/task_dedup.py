from datetime import datetime, timedelta

INFLIGHT_TASK_STATUSES = frozenset(
    {"pending", "scraping", "crawling", "reporting", "processing", "retrying", "running"}
)


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


def norm_category_code_for_dedup(category_id):
    normalized = str(category_id or "").strip().lstrip("0")
    return normalized if normalized else "0"


def evaluate_category_task_block(tasks, category_id, recent_limit_iso):
    """Return a blocking task when the category is in-flight or recently completed."""
    target_norm = norm_category_code_for_dedup(category_id)
    completed_recent = None

    for task in tasks or []:
        if norm_category_code_for_dedup(task.get("category_id")) != target_norm:
            continue

        status = (task.get("status") or "").strip().lower()
        if status in INFLIGHT_TASK_STATUSES:
            return {"kind": "inflight", "task": task}

        if status == "completed":
            created_at = task.get("created_at") or ""
            if created_at >= recent_limit_iso:
                if (
                    not completed_recent
                    or created_at > (completed_recent.get("created_at") or "")
                ):
                    completed_recent = task

    if completed_recent:
        return {"kind": "completed_recent", "task": completed_recent}
    return None


def recent_task_limit_iso(recent_days=15):
    return (datetime.now() - timedelta(days=recent_days)).isoformat()
