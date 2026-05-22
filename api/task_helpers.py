import json
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Sequence

RUNNING_TASK_STATUSES = frozenset(
    {"pending", "scraping", "crawling", "reporting", "processing", "retrying"}
)


def get_task_valid_product_count(task):
    """Return valid product count from task category_stats, tolerating messy payloads."""
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


def expand_status_filters(status_filters: Optional[Iterable[str]]) -> List[str]:
    if not status_filters:
        return []

    if isinstance(status_filters, str):
        raw_filters = [status_filters]
    else:
        raw_filters = list(status_filters)

    expanded: List[str] = []
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


def parse_task_timestamp(value) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def task_matches_days(task: dict, days: Optional[int]) -> bool:
    if not days or days <= 0:
        return True
    created_at = parse_task_timestamp(task.get("created_at"))
    if not created_at:
        return False
    return created_at >= (datetime.now(created_at.tzinfo) - timedelta(days=days))


def task_matches_status_filters(task: dict, expanded_statuses: Sequence[str]) -> bool:
    if not expanded_statuses:
        return True
    return (task.get("status") or "").strip().lower() in expanded_statuses
