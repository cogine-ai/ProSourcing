#!/usr/bin/env python3
"""
One-off backfill for issue #39.

Backfill each task's cluster/category brand count directly from the collected
RPA JSON files:

  rpa_output_<task_id>.json -> niche_stats.sale_brand_qty

Target:
- analysis_tasks.category_stats.brand_qty
- analysis_tasks.category_stats.brand_count

Usage:
  python scripts/backfill_brand_counts.py
  python scripts/backfill_brand_counts.py --dry-run
"""

from __future__ import annotations

import argparse
import glob
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


def extract_brand_count(stats: dict) -> int:
    return max(
        force_int(stats.get("brand_qty")),
        force_int(stats.get("brand_count")),
        force_int(stats.get("sale_brand_qty")),
    )


def discover_task_jsons() -> Dict[str, str]:
    patterns = [
        os.path.join("output", "json", "rpa_output_*.json"),
        os.path.join("output", "rpa_output_*.json"),
        os.path.join("logs", "rpa_output_*.json"),
    ]

    files_by_task: Dict[str, str] = {}
    for pattern in patterns:
        for path in glob.glob(pattern):
            name = os.path.basename(path)
            if not name.startswith("rpa_output_") or not name.endswith(".json"):
                continue
            task_id = name[len("rpa_output_"):-len(".json")]
            files_by_task.setdefault(task_id, path)
    return files_by_task


def load_brand_counts_from_json() -> Dict[str, Tuple[int, str]]:
    files_by_task = discover_task_jsons()
    result: Dict[str, Tuple[int, str]] = {}

    for task_id, path in files_by_task.items():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception:
            continue

        niche_stats = payload.get("niche_stats") or {}
        brand_count = extract_brand_count(niche_stats)
        if brand_count > 0:
            result[task_id] = (brand_count, path)

    return result


def fetch_task_updates(cur, json_brand_counts: Dict[str, Tuple[int, str]]):
    cur.execute(
        """
        SELECT id::text, category_stats
        FROM analysis_tasks
        WHERE status = 'completed'
          AND category_stats IS NOT NULL
        """
    )

    updates = []
    for task_id, category_stats in cur.fetchall():
        source = json_brand_counts.get(task_id)
        if not source:
            continue

        json_brand_count, source_path = source
        stats = category_stats if isinstance(category_stats, dict) else {}
        current_brand_count = extract_brand_count(stats)

        if current_brand_count > 0 and force_int(stats.get("brand_qty")) > 0 and force_int(stats.get("brand_count")) > 0:
            continue

        next_stats = dict(stats)
        next_stats["brand_qty"] = json_brand_count
        next_stats["brand_count"] = json_brand_count
        updates.append((task_id, next_stats, current_brand_count, json_brand_count, source_path))

    return updates


def apply_task_updates(cur, updates: Iterable[Tuple[str, dict, int, int, str]]):
    rows = [(task_id, Json(category_stats)) for task_id, category_stats, _, _, _ in updates]
    execute_values(
        cur,
        """
        UPDATE analysis_tasks AS t
        SET category_stats = v.category_stats::jsonb
        FROM (VALUES %s) AS v(id, category_stats)
        WHERE t.id::text = v.id
        """,
        rows,
        template="(%s, %s)",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing database updates")
    args = parser.parse_args()

    json_brand_counts = load_brand_counts_from_json()
    print(f"[INFO] task_json_brand_sources={len(json_brand_counts)}")

    with get_conn() as conn:
        with conn.cursor() as cur:
            task_updates = list(fetch_task_updates(cur, json_brand_counts))
            print(f"[INFO] analysis_tasks_category_stats_updates={len(task_updates)}")

            if task_updates[:10]:
                sample = [
                    {
                        "task_id": task_id,
                        "old_brand_count": old_count,
                        "new_brand_count": new_count,
                        "source": source_path,
                    }
                    for task_id, _, old_count, new_count, source_path in task_updates[:10]
                ]
                print("[SAMPLE]", json.dumps(sample, ensure_ascii=False, indent=2))

            if args.dry_run:
                print("[DRY-RUN] no database changes applied")
                return

            if task_updates:
                apply_task_updates(cur, task_updates)

        conn.commit()

    print("[DONE] task category_stats brand count backfill completed")


if __name__ == "__main__":
    main()
