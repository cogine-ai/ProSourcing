#!/usr/bin/env python3
"""
One-off brand count backfill for issue #39.

What it does:
1) Loads top-category brand counts from full_category_data.json stats.
2) Backfills algatop_top_category_stats.brand_count where current value is null/0.
3) Backfills analysis_tasks.category_stats.brand_qty / brand_count for completed tasks.

Usage:
  python scripts/backfill_brand_counts.py
  python scripts/backfill_brand_counts.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Dict, Iterable, Optional, Tuple

import psycopg2
from psycopg2.extras import Json, execute_values


def force_int(value) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)

    text = str(value).strip().replace(" ", "").replace(",", "")
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else 0


def norm_code(value) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return raw.zfill(5) if raw.isdigit() else raw


def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)

    host = os.getenv("PG_HOST", "127.0.0.1")
    port = int(os.getenv("PG_PORT", "5432"))
    user = os.getenv("PG_USER", "postgres")
    password = os.getenv("PG_PASSWORD", "prosourcing123")
    dbname = os.getenv("PG_DB", "prosourcing")
    return psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)


def find_data_file() -> Optional[str]:
    candidates = [
        os.path.join("scripts", "full_category_data.json"),
        os.path.join("deployment_package", "scripts", "full_category_data.json"),
        "full_category_data.json",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def extract_brand_count(item: dict) -> int:
    return max(
        force_int(item.get("brand_count")),
        force_int(item.get("brand_qty")),
        force_int(item.get("sale_brand_qty")),
    )


def load_top_category_brand_counts() -> Dict[str, int]:
    data_file = find_data_file()
    if not data_file:
        raise FileNotFoundError("full_category_data.json not found in known locations")

    with open(data_file, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    stats = payload.get("stats", []) if isinstance(payload, dict) else []
    mapping: Dict[str, int] = {}

    for item in stats:
        if not isinstance(item, dict):
            continue
        category_id = norm_code(item.get("algatop_id") or item.get("id"))
        brand_count = extract_brand_count(item)
        if category_id and brand_count > 0:
            mapping[category_id] = brand_count

    return mapping


def fetch_stats_updates(cur, source_map: Dict[str, int]) -> Iterable[Tuple[str, int]]:
    cur.execute("SELECT algatop_id::text, COALESCE(brand_count, 0) FROM algatop_top_category_stats")
    updates = []
    for category_id, current_brand_count in cur.fetchall():
        normalized = norm_code(category_id)
        candidate = source_map.get(normalized, 0)
        if candidate > 0 and force_int(current_brand_count) <= 0:
            updates.append((normalized, candidate))
    return updates


def fetch_task_updates(cur, source_map: Dict[str, int]):
    cur.execute(
        """
        SELECT id,
               category_id::text,
               category_stats
        FROM analysis_tasks
        WHERE status = 'completed'
          AND category_stats IS NOT NULL
        """
    )

    updates = []
    for task_id, category_id, category_stats in cur.fetchall():
        stats = category_stats if isinstance(category_stats, dict) else {}
        current_brand_qty = extract_brand_count(stats)
        fallback_brand_qty = source_map.get(norm_code(category_id), 0)
        target_brand_qty = current_brand_qty if current_brand_qty > 0 else fallback_brand_qty

        if target_brand_qty <= 0:
            continue

        needs_update = force_int(stats.get("brand_qty")) <= 0 or force_int(stats.get("brand_count")) <= 0
        if not needs_update:
            continue

        next_stats = dict(stats)
        next_stats["brand_qty"] = target_brand_qty
        next_stats["brand_count"] = target_brand_qty
        updates.append((task_id, next_stats, current_brand_qty, fallback_brand_qty))

    return updates


def apply_stats_updates(cur, updates: Iterable[Tuple[str, int]]):
    execute_values(
        cur,
        """
        UPDATE algatop_top_category_stats AS t
        SET brand_count = v.brand_count,
            updated_at = timezone('utc', now())
        FROM (VALUES %s) AS v(algatop_id, brand_count)
        WHERE t.algatop_id::text = v.algatop_id
        """,
        list(updates),
    )


def apply_task_updates(cur, updates):
    execute_values(
        cur,
        """
        UPDATE analysis_tasks AS t
        SET category_stats = v.category_stats::jsonb
        FROM (VALUES %s) AS v(id, category_stats)
        WHERE t.id = v.id::uuid
        """,
        [(task_id, Json(category_stats)) for task_id, category_stats, _, _ in updates],
        template="(%s, %s)",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing database updates")
    args = parser.parse_args()

    source_map = load_top_category_brand_counts()
    print(f"[INFO] loaded_source_brand_counts={len(source_map)}")

    with get_conn() as conn:
        with conn.cursor() as cur:
            stats_updates = list(fetch_stats_updates(cur, source_map))
            task_updates = list(fetch_task_updates(cur, source_map))

            print(f"[INFO] algatop_top_category_stats_updates={len(stats_updates)}")
            print(f"[INFO] analysis_tasks_category_stats_updates={len(task_updates)}")

            if stats_updates[:5]:
                print("[SAMPLE] stats_updates", stats_updates[:5])
            if task_updates[:5]:
                sample = [(task_id, payload.get("brand_qty"), current, fallback) for task_id, payload, current, fallback in task_updates[:5]]
                print("[SAMPLE] task_updates", sample)

            if args.dry_run:
                print("[DRY-RUN] no database changes applied")
                return

            if stats_updates:
                apply_stats_updates(cur, stats_updates)
            if task_updates:
                apply_task_updates(cur, task_updates)

        conn.commit()

    print("[DONE] brand count backfill completed")


if __name__ == "__main__":
    main()
