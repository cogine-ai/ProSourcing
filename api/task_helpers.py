"""Pure helpers for task history filtering and category code normalization."""

from __future__ import annotations

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
