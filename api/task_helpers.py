"""Pure task and category helpers for the API layer (stdlib-only for unit tests)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Iterable, List, Optional, Sequence, Set

RUNNING_TASK_STATUSES = frozenset(
    {"pending", "scraping", "crawling", "reporting", "processing", "retrying"}
)


def get_task_valid_product_count(task: dict) -> int:
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


def normalize_category_code(category_id: Any) -> str:
    raw = str(category_id or "").strip()
    if not raw:
        return ""
    return raw.zfill(5) if raw.isdigit() else raw


def category_code_variants(category_id: Any) -> List[str]:
    raw = str(category_id or "").strip()
    if not raw:
        return []

    variants: List[str] = []
    for candidate in (raw, raw.zfill(5) if raw.isdigit() else raw, raw.lstrip("0") or "0"):
        candidate = str(candidate).strip()
        if candidate and candidate not in variants:
            variants.append(candidate)
    return variants


def extract_category_aliases(category_value: Any) -> Set[str]:
    aliases: Set[str] = set()
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


def normalize_up_categories(up_categories: Any) -> list:
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


def parse_task_timestamp(value: Any) -> Optional[datetime]:
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
