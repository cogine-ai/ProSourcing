#!/usr/bin/env python3
"""
Backfill last crawl dates for categories.

What it does:
1) Reads all category ids from algatop_categories_master.
2) Reads completed task dates from multiple sources.
3) Computes latest date per normalized category id (supports "44"/"00044").
4) Writes results to category_last_crawl_dates table (upsert).
5) If algatop_categories_master.last_crawl_date exists, updates it too.

Usage:
  python scripts/backfill_last_crawl_date.py
  python scripts/backfill_last_crawl_date.py --dry-run
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from typing import Dict, Iterable, Tuple

import psycopg2
from psycopg2.extras import execute_values


def norm_code(v: str) -> str:
    s = str(v or "").strip().lstrip("0")
    return s if s else "0"


def get_conn():
    # Prefer DATABASE_URL (same style as backend)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)

    # Fallback PG_* vars
    host = os.getenv("PG_HOST", "127.0.0.1")
    port = int(os.getenv("PG_PORT", "5432"))
    user = os.getenv("PG_USER", "postgres")
    pwd = os.getenv("PG_PASSWORD", "prosourcing123")
    db = os.getenv("PG_DB", "prosourcing")
    return psycopg2.connect(host=host, port=port, user=user, password=pwd, dbname=db)


def table_exists(cur, table: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = %s
        LIMIT 1
        """,
        (table,),
    )
    return cur.fetchone() is not None


def fetch_master_ids(cur) -> Tuple[Dict[str, str], Dict[str, str]]:
    cur.execute(
        """
        SELECT algatop_id::text, is_leaf
        FROM algatop_categories_master
        """
    )
    all_ids: Dict[str, str] = {}
    leaf_ids: Dict[str, str] = {}
    for raw_id, is_leaf in cur.fetchall():
        canonical = str(raw_id)
        normalized = norm_code(raw_id)
        all_ids[normalized] = canonical
        if is_leaf:
            leaf_ids[normalized] = canonical
    return all_ids, leaf_ids


def update_latest(latest: Dict[str, str], category_id: str, dt: str):
    if not category_id or not dt:
        return
    key = norm_code(category_id)
    if key not in latest or dt > latest[key]:
        latest[key] = dt


def fetch_completed_task_dates(cur, latest: Dict[str, str]) -> int:
    cur.execute(
        """
        SELECT category_id::text,
               COALESCE(updated_at, created_at)::date::text AS dt
        FROM analysis_tasks
        WHERE status = 'completed'
          AND category_id IS NOT NULL
          AND COALESCE(updated_at, created_at) IS NOT NULL
        """
    )
    rows = 0
    for category_id, dt in cur.fetchall():
        update_latest(latest, category_id, dt)
        rows += 1
    return rows


def fetch_backup_task_dates(cur, latest: Dict[str, str]) -> int:
    if not table_exists(cur, "analysis_tasks_category_id_backup"):
        return 0

    cur.execute(
        """
        SELECT b.old_category_id::text,
               COALESCE(t.updated_at, t.created_at)::date::text AS dt
        FROM analysis_tasks_category_id_backup AS b
        JOIN analysis_tasks AS t ON t.id = b.id
        WHERE t.status = 'completed'
          AND b.old_category_id IS NOT NULL
          AND COALESCE(t.updated_at, t.created_at) IS NOT NULL
        """
    )
    rows = 0
    for category_id, dt in cur.fetchall():
        update_latest(latest, category_id, dt)
        rows += 1
    return rows


def fetch_raw_data_dates(cur, latest: Dict[str, str]) -> int:
    if not table_exists(cur, "products_raw_data"):
        return 0

    cur.execute(
        """
        SELECT DISTINCT ON (task_id, category_ext_id::text)
               category_ext_id::text,
               COALESCE(t.updated_at, t.created_at)::date::text AS dt
        FROM products_raw_data AS p
        JOIN analysis_tasks AS t ON t.id = p.task_id
        WHERE t.status = 'completed'
          AND p.category_ext_id IS NOT NULL
          AND COALESCE(t.updated_at, t.created_at) IS NOT NULL
        """
    )
    rows = 0
    for category_id, dt in cur.fetchall():
        update_latest(latest, category_id, dt)
        rows += 1
    return rows


def table_has_column(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def ensure_cache_table(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS category_last_crawl_dates (
          category_code text PRIMARY KEY,
          last_crawl_date date NOT NULL,
          updated_at timestamptz NOT NULL DEFAULT timezone('utc', now())
        )
        """
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Compute only, do not write DB")
    args = parser.parse_args()

    with get_conn() as conn:
        with conn.cursor() as cur:
            all_map, leaf_map = fetch_master_ids(cur)  # norm -> canonical algatop_id
            task_latest: Dict[str, str] = {}
            task_rows = fetch_completed_task_dates(cur, task_latest)
            backup_rows = fetch_backup_task_dates(cur, task_latest)
            raw_rows = fetch_raw_data_dates(cur, task_latest)

            matched: Iterable[Tuple[str, str]] = [
                (all_map[norm_id], dt)
                for norm_id, dt in task_latest.items()
                if norm_id in all_map
            ]
            matched = list(matched)
            matched_leaf = [item for item in matched if norm_code(item[0]) in leaf_map]

            print(f"all_category_count={len(all_map)}")
            print(f"leaf_count={len(leaf_map)}")
            print(f"completed_task_rows={task_rows}")
            print(f"backup_task_rows={backup_rows}")
            print(f"raw_data_rows={raw_rows}")
            print(f"completed_task_categories={len(task_latest)}")
            print(f"matched_category_dates={len(matched)}")
            print(f"matched_leaf_dates={len(matched_leaf)}")
            if matched:
                print("sample=", matched[:10])

            if args.dry_run:
                print("dry-run mode: no DB writes")
                return

            if not matched:
                print("no matched categories found, skipped DB writes")
                return

            ensure_cache_table(cur)
            execute_values(
                cur,
                """
                INSERT INTO category_last_crawl_dates (category_code, last_crawl_date, updated_at)
                VALUES %s
                ON CONFLICT (category_code) DO UPDATE
                SET last_crawl_date = EXCLUDED.last_crawl_date,
                    updated_at = EXCLUDED.updated_at
                """,
                [(code, dt, datetime.now(timezone.utc)) for code, dt in matched],
                page_size=1000,
            )

            # Optional: sync to master table if column exists
            if table_has_column(cur, "algatop_categories_master", "last_crawl_date"):
                execute_values(
                    cur,
                    """
                    UPDATE algatop_categories_master AS m
                    SET last_crawl_date = v.last_crawl_date::date
                    FROM (VALUES %s) AS v(algatop_id, last_crawl_date)
                    WHERE m.algatop_id::text = v.algatop_id
                    """,
                    matched,
                    page_size=1000,
                )
                print("synced algatop_categories_master.last_crawl_date")
            else:
                print("algatop_categories_master.last_crawl_date not found, skipped")

            conn.commit()
            print("backfill done")


if __name__ == "__main__":
    main()
