#!/usr/bin/env python3
"""
Backfill empty analysis_tasks.category_id safely.

Rules:
1) Only rows with empty category_id are eligible.
2) Match only leaf categories in algatop_categories_master.
3) Update only when exactly one leaf id is matched (unambiguous).
4) Backup target rows before update into analysis_tasks_category_id_backup.

Match priority:
- p1: task.category == name_cn
- p2: task.category == name_ru
- p3: Chinese text inside parentheses in task.category equals name_cn
- p4: middle token in "RPA采集_xxx_yyy" equals name_cn or name_ru

Usage:
  python scripts/backfill_empty_category_id.py --dry-run
  python scripts/backfill_empty_category_id.py
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

import psycopg2
from psycopg2.extras import execute_values


@dataclass
class TaskRow:
    task_id: str
    category_raw: str


def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)

    host = os.getenv("PG_HOST", "127.0.0.1")
    port = int(os.getenv("PG_PORT", "5432"))
    user = os.getenv("PG_USER", "postgres")
    pwd = os.getenv("PG_PASSWORD", "prosourcing123")
    db = os.getenv("PG_DB", "prosourcing")
    return psycopg2.connect(host=host, port=port, user=user, password=pwd, dbname=db)


def clean_text(s: Optional[str]) -> str:
    return (s or "").strip()


def norm_id_for_store(s: str) -> str:
    s = str(s or "").strip()
    return s.zfill(5) if s.isdigit() else s


def extract_paren_text(s: str) -> Optional[str]:
    m = re.search(r"\(([^()]*)\)", s)
    if not m:
        return None
    out = clean_text(m.group(1))
    return out if out else None


def extract_rpa_middle(s: str) -> Optional[str]:
    # Example: RPA采集_智能手机_2026-04-01
    if not s.startswith("RPA采集_"):
        return None
    parts = s.split("_")
    if len(parts) < 3:
        return None
    out = clean_text(parts[1])
    return out if out else None


def fetch_empty_tasks(cur) -> List[TaskRow]:
    cur.execute(
        """
        SELECT id::text, trim(category) AS category_raw
        FROM analysis_tasks
        WHERE COALESCE(category_id, '') = ''
          AND COALESCE(trim(category), '') <> ''
        """
    )
    rows = []
    for task_id, category_raw in cur.fetchall():
        rows.append(TaskRow(task_id=str(task_id), category_raw=clean_text(category_raw)))
    return rows


def fetch_leaf_master(cur) -> List[Tuple[str, str, str]]:
    cur.execute(
        """
        SELECT algatop_id::text, trim(COALESCE(name_cn, '')), trim(COALESCE(name_ru, ''))
        FROM algatop_categories_master
        WHERE is_leaf = TRUE
        """
    )
    out: List[Tuple[str, str, str]] = []
    for raw_id, name_cn, name_ru in cur.fetchall():
        out.append((norm_id_for_store(str(raw_id)), clean_text(name_cn), clean_text(name_ru)))
    return out


def build_indexes(
    leaf_rows: Sequence[Tuple[str, str, str]],
) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    by_cn: Dict[str, Set[str]] = {}
    by_ru: Dict[str, Set[str]] = {}
    for leaf_id, name_cn, name_ru in leaf_rows:
        if name_cn:
            by_cn.setdefault(name_cn, set()).add(leaf_id)
        if name_ru:
            by_ru.setdefault(name_ru, set()).add(leaf_id)
    return by_cn, by_ru


def unique_match(
    task_category: str,
    by_cn: Dict[str, Set[str]],
    by_ru: Dict[str, Set[str]],
) -> Tuple[Optional[str], str]:
    # p1: exact cn
    hit = set(by_cn.get(task_category, set()))
    if len(hit) == 1:
        return next(iter(hit)), "p1_exact_cn"
    if len(hit) > 1:
        return None, "ambiguous_p1"

    # p2: exact ru
    hit = set(by_ru.get(task_category, set()))
    if len(hit) == 1:
        return next(iter(hit)), "p2_exact_ru"
    if len(hit) > 1:
        return None, "ambiguous_p2"

    # p3: inside parentheses -> cn
    paren = extract_paren_text(task_category)
    if paren:
        hit = set(by_cn.get(paren, set()))
        if len(hit) == 1:
            return next(iter(hit)), "p3_paren_cn"
        if len(hit) > 1:
            return None, "ambiguous_p3"

    # p4: RPA middle token -> cn/ru
    mid = extract_rpa_middle(task_category)
    if mid:
        hit = set(by_cn.get(mid, set())) | set(by_ru.get(mid, set()))
        if len(hit) == 1:
            return next(iter(hit)), "p4_rpa_mid"
        if len(hit) > 1:
            return None, "ambiguous_p4"

    return None, "no_match"


def ensure_backup_table(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_tasks_category_id_backup (
          id uuid PRIMARY KEY,
          old_category_id text,
          category text,
          backed_up_at timestamptz NOT NULL DEFAULT timezone('utc', now())
        )
        """
    )


def backup_rows(cur, task_ids: Sequence[str]):
    if not task_ids:
        return 0
    values = [(tid,) for tid in task_ids]
    execute_values(
        cur,
        """
        INSERT INTO analysis_tasks_category_id_backup (id, old_category_id, category, backed_up_at)
        SELECT t.id, t.category_id, t.category, timezone('utc', now())
        FROM analysis_tasks t
        JOIN (VALUES %s) AS v(id) ON t.id::text = v.id
        ON CONFLICT (id) DO NOTHING
        """,
        values,
        template="(%s)",
        page_size=1000,
        fetch=False,
    )
    return len(task_ids)


def update_category_ids(cur, updates: Sequence[Tuple[str, str]]) -> int:
    if not updates:
        return 0
    execute_values(
        cur,
        """
        UPDATE analysis_tasks AS t
        SET category_id = v.category_id
        FROM (VALUES %s) AS v(task_id, category_id)
        WHERE t.id::text = v.task_id
          AND COALESCE(t.category_id, '') = ''
        """,
        updates,
        page_size=1000,
    )
    return len(updates)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not write DB")
    parser.add_argument("--sample", type=int, default=20, help="How many sample rows to print")
    args = parser.parse_args()

    with get_conn() as conn:
        with conn.cursor() as cur:
            tasks = fetch_empty_tasks(cur)
            leaf_rows = fetch_leaf_master(cur)
            by_cn, by_ru = build_indexes(leaf_rows)

            matched_updates: List[Tuple[str, str]] = []
            ambiguous: List[Tuple[str, str]] = []
            no_match: List[Tuple[str, str]] = []
            reasons: Dict[str, int] = {}

            for row in tasks:
                leaf_id, reason = unique_match(row.category_raw, by_cn, by_ru)
                reasons[reason] = reasons.get(reason, 0) + 1
                if leaf_id:
                    matched_updates.append((row.task_id, leaf_id))
                elif reason.startswith("ambiguous"):
                    ambiguous.append((row.task_id, row.category_raw))
                else:
                    no_match.append((row.task_id, row.category_raw))

            print(f"empty_tasks={len(tasks)}")
            print(f"leaf_categories={len(leaf_rows)}")
            print(f"matched_unique={len(matched_updates)}")
            print(f"ambiguous={len(ambiguous)}")
            print(f"no_match={len(no_match)}")
            print("reason_stats=", reasons)

            if matched_updates:
                print("sample_updates=", matched_updates[: args.sample])
            if ambiguous:
                print("sample_ambiguous=", ambiguous[: args.sample])
            if no_match:
                print("sample_no_match=", no_match[: args.sample])

            if args.dry_run:
                print("dry-run mode: no DB writes")
                return

            ensure_backup_table(cur)
            task_ids = [tid for tid, _ in matched_updates]
            backup_rows(cur, task_ids)
            update_category_ids(cur, matched_updates)
            conn.commit()
            print(f"updated_rows={len(matched_updates)}")
            print("done")


if __name__ == "__main__":
    main()
