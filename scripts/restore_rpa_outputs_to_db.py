#!/usr/bin/env python3
"""
Batch restore historical local RPA JSON outputs into the business database.

Targets:
- analysis_tasks
- products_raw_data
- products_calculated_metrics

This script reads JSON files from the local machine, not from inside a
container. By default it scans:

    output/json/rpa_output_*.json

Usage:
    python scripts/restore_rpa_outputs_to_db.py
    python scripts/restore_rpa_outputs_to_db.py --pattern "D:/data/rpa_output_*.json"
    python scripts/restore_rpa_outputs_to_db.py --only-missing-tasks
    python scripts/restore_rpa_outputs_to_db.py --dry-run
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dotenv import load_dotenv


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from core.scoring import ScoringEngine


DEFAULT_PATTERN = os.path.join(PROJECT_ROOT, "output", "json", "rpa_output_*.json")


@dataclass
class RestoreResult:
    source_path: str
    task_id: str
    created_task: bool
    raw_count: int
    calc_count: int


def load_pg_driver():
    try:
        import psycopg2  # type: ignore
        from psycopg2.extras import Json, execute_values  # type: ignore

        return psycopg2, Json, execute_values
    except ModuleNotFoundError:
        try:
            import psycopg  # type: ignore
            from psycopg.types.json import Json  # type: ignore

            def execute_values(cur, query: str, rows: Sequence[Tuple[Any, ...]]) -> None:
                if not rows:
                    return
                placeholder = ",".join(["%s"] * len(rows))
                cur.execute(query.replace("%s", placeholder, 1), rows)

            return psycopg, Json, execute_values
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "PostgreSQL driver not found. Install one of:\n"
                "  pip install psycopg2-binary\n"
                "or\n"
                "  pip install psycopg\n"
                "or run:\n"
                "  pip install -r requirements.txt"
            ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restore local rpa_output_*.json files into PostgreSQL business tables."
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help="Glob pattern for local JSON files. Default: %(default)s",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only process the first N matched files after sorting. 0 means no limit.",
    )
    parser.add_argument(
        "--task-id",
        action="append",
        default=[],
        help="Only restore the specified task id. Can be passed multiple times.",
    )
    parser.add_argument(
        "--only-missing-tasks",
        action="store_true",
        help="Skip files whose task already exists in analysis_tasks.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview matched files and computed actions without writing database changes.",
    )
    return parser.parse_args()


def get_connection():
    load_dotenv()
    psycopg_module, _, _ = load_pg_driver()

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg_module.connect(db_url)

    host = os.getenv("PG_HOST", "127.0.0.1")
    port = int(os.getenv("PG_PORT", "5432"))
    user = os.getenv("PG_USER", "postgres")
    password = os.getenv("PG_PASSWORD", "prosourcing123")
    dbname = os.getenv("PG_DB", "prosourcing")
    return psycopg_module.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
    )


def force_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    text = str(value).strip().replace(" ", "").replace(",", "")
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else 0


def force_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal(int(value))
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    text = str(value).strip().replace(" ", "").replace(",", "")
    if not text:
        return Decimal("0")
    try:
        return Decimal(text)
    except Exception:
        digits = "".join(ch for ch in text if ch.isdigit() or ch in ".-")
        return Decimal(digits) if digits else Decimal("0")


def json_safe(obj: Any) -> Any:
    if obj is None:
        return None
    try:
        json.dumps(obj, ensure_ascii=False)
        return obj
    except (TypeError, ValueError):
        return None


def is_valid_uuid(value: Any) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except Exception:
        return False


def parse_created_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None

    text = str(value).strip()
    if not text:
        return None

    candidates = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
    ]
    base = text.split(".")[0]
    for fmt in candidates:
        try:
            return datetime.strptime(base, fmt)
        except ValueError:
            continue
    return None


def discover_files(pattern: str, selected_task_ids: Sequence[str], limit: int) -> List[str]:
    paths = sorted(glob.glob(pattern))
    if selected_task_ids:
        allowed = set(selected_task_ids)
        filtered = []
        for path in paths:
            task_id = task_id_from_path(path)
            if task_id in allowed:
                filtered.append(path)
        paths = filtered

    if limit > 0:
        paths = paths[:limit]
    return paths


def task_id_from_path(path: str) -> Optional[str]:
    name = os.path.basename(path)
    if not (name.startswith("rpa_output_") and name.endswith(".json")):
        return None
    return name[len("rpa_output_") : -len(".json")]


def task_exists(cur, task_id: str) -> bool:
    cur.execute("SELECT 1 FROM analysis_tasks WHERE id = %s LIMIT 1", (task_id,))
    return cur.fetchone() is not None


def derive_task_name(niche_stats: Dict[str, Any], source_path: str) -> str:
    category_name = (
        niche_stats.get("category_name")
        or niche_stats.get("niche_name")
        or niche_stats.get("category_ext_name")
        or "RPA恢复任务"
    )
    stem = os.path.splitext(os.path.basename(source_path))[0]
    return f"{category_name}_{stem}"


def contains_chinese(text: Any) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in str(text or ""))


def extract_cn_name_from_up_categories(up_categories: Any) -> Optional[str]:
    if not isinstance(up_categories, list):
        return None

    for item in reversed(up_categories):
        if isinstance(item, dict):
            for key in ("name_cn", "category_name_cn", "category_cn", "category_name"):
                value = str(item.get(key) or "").strip()
                if value and contains_chinese(value):
                    return value
        elif isinstance(item, str):
            value = item.strip()
            if value and contains_chinese(value):
                return value
    return None


def lookup_category_name_cn(cur, category_id: Any) -> Optional[str]:
    category_code = str(category_id or "").strip()
    if not category_code:
        return None

    cur.execute(
        """
        SELECT name_cn
        FROM algatop_categories_master
        WHERE algatop_id = %s
        LIMIT 1
        """,
        (category_code,),
    )
    row = cur.fetchone()
    if not row or not row[0]:
        return None

    value = str(row[0]).strip()
    return value or None


def derive_task_display_name(cur, niche_stats: Dict[str, Any]) -> str:
    category_name = (
        extract_cn_name_from_up_categories(niche_stats.get("up_categories_json"))
        or lookup_category_name_cn(cur, niche_stats.get("category_ext_id"))
        or lookup_category_name_cn(cur, niche_stats.get("category_id"))
    )
    if category_name:
        return category_name

    for key in ("category_name", "niche_name", "category_ext_name"):
        value = str(niche_stats.get(key) or "").strip()
        if value and contains_chinese(value):
            return value

    return "RPA恢复任务"


def build_or_update_task(cur, task_id_hint: Optional[str], niche_stats: Dict[str, Any], trend: Any, source_path: str) -> Tuple[str, bool]:
    _, Json, _ = load_pg_driver()
    task_payload = {
        "category": derive_task_display_name(cur, niche_stats),
        "status": "completed",
        "category_id": niche_stats.get("category_ext_id") or niche_stats.get("category_id"),
        "category_stats": Json(json_safe(niche_stats)),
        "trend_data": Json(json_safe(trend)),
        "up_categories": Json(json_safe(niche_stats.get("up_categories_json"))),
    }

    if task_id_hint and is_valid_uuid(task_id_hint):
        task_payload_with_id = {"id": task_id_hint, **task_payload}
        cur.execute(
            """
            INSERT INTO analysis_tasks (id, category, status, category_id, category_stats, trend_data, up_categories)
            VALUES (%(id)s, %(category)s, %(status)s, %(category_id)s, %(category_stats)s, %(trend_data)s, %(up_categories)s)
            ON CONFLICT (id) DO UPDATE
            SET category = EXCLUDED.category,
                status = EXCLUDED.status,
                category_id = EXCLUDED.category_id,
                category_stats = EXCLUDED.category_stats,
                trend_data = EXCLUDED.trend_data,
                up_categories = EXCLUDED.up_categories
            RETURNING (xmax = 0) AS inserted
            """,
            task_payload_with_id,
        )
        inserted = bool(cur.fetchone()[0])
        return task_id_hint, inserted

    cur.execute(
        """
        INSERT INTO analysis_tasks (category, status, category_id, category_stats, trend_data, up_categories)
        VALUES (%(category)s, %(status)s, %(category_id)s, %(category_stats)s, %(trend_data)s, %(up_categories)s)
        RETURNING id
        """,
        task_payload,
    )
    return str(cur.fetchone()[0]), True


def compute_category_level_stats(niche_stats: Dict[str, Any], products: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    enriched = dict(niche_stats or {})

    sorted_by_revenue = sorted(products, key=lambda item: force_decimal(item.get("sale_amount")), reverse=True)
    top3_revenue = sum(force_decimal(item.get("sale_amount")) for item in sorted_by_revenue[:3])
    total_amount = force_decimal(enriched.get("sale_amount"))
    if total_amount <= 0:
        total_amount = sum(force_decimal(item.get("sale_amount")) for item in products)

    sale_product_qty = force_int(enriched.get("sale_product_qty"))
    if sale_product_qty <= 0:
        sale_product_qty = len(products)

    brand_qty = max(
        force_int(enriched.get("brand_qty")),
        force_int(enriched.get("brand_count")),
        force_int(enriched.get("sale_brand_qty")),
    )
    merchant_qty = max(
        force_int(enriched.get("sale_merchant_qty")),
        force_int(enriched.get("sale_seller_qty")),
        force_int(enriched.get("merchant_qty")),
    )

    valid_product_count = 0
    now = datetime.now()
    for item in products:
        monthly_sales = force_int(item.get("sale_qty"))
        reviews = force_int(item.get("review_qty"))
        price = force_decimal(item.get("sale_price"))
        created_dt = parse_created_dt(item.get("created_dt"))
        days_since_creation = (now - created_dt).days if created_dt else 999
        if monthly_sales >= 60 and reviews >= 15 and price >= Decimal("800") and days_since_creation <= 300:
            valid_product_count += 1

    cr3_ratio = Decimal("0")
    if total_amount > 0:
        cr3_ratio = (top3_revenue / total_amount) * Decimal("100")

    enriched["top3_revenue"] = float(top3_revenue)
    enriched["sale_amount"] = float(total_amount)
    enriched["sale_product_qty"] = sale_product_qty
    enriched["brand_qty"] = brand_qty
    enriched["brand_count"] = brand_qty
    enriched["sale_merchant_qty"] = merchant_qty
    enriched["valid_product_count"] = valid_product_count
    enriched["valid_product_qty"] = valid_product_count
    enriched["cr3"] = f"{cr3_ratio.quantize(Decimal('0.1'))}%"
    return enriched


def build_payloads(task_id: str, niche_stats: Dict[str, Any], products: Sequence[Dict[str, Any]]) -> Tuple[List[Tuple[Any, ...]], List[Tuple[Any, ...]]]:
    _, Json, _ = load_pg_driver()
    category_sales = force_decimal(niche_stats.get("sale_qty"))
    category_product_count = force_decimal(niche_stats.get("sale_product_qty"))
    avg_sales_per_listing = Decimal("0")
    if category_product_count > 0:
        avg_sales_per_listing = category_sales / category_product_count

    raw_rows: List[Tuple[Any, ...]] = []
    calc_rows: List[Tuple[Any, ...]] = []
    now = datetime.now()

    for item in products:
        sku = str(item.get("product_code") or item.get("sku") or "").strip()
        if not sku:
            continue

        monthly_sales = force_int(item.get("sale_qty"))
        reviews = force_int(item.get("review_qty"))
        price = force_decimal(item.get("sale_price"))
        created_dt = parse_created_dt(item.get("created_dt"))

        days_since_creation = (now - created_dt).days if created_dt else 0
        monthly_sales_score = ScoringEngine.score_monthly_sales(monthly_sales)
        review_score = ScoringEngine.score_reviews(reviews)
        price_score = ScoringEngine.score_price(float(price))
        avg_sales_score = ScoringEngine.score_avg_sales_per_listing(float(avg_sales_per_listing))
        days_per_review_score = ScoringEngine.score_days_per_review(days_since_creation, reviews)
        total_score = monthly_sales_score + review_score + price_score + avg_sales_score + days_per_review_score

        preview_image_list = item.get("preview_image_list")
        if isinstance(preview_image_list, str):
            try:
                preview_image_list = json.loads(preview_image_list)
            except Exception:
                pass

        raw_rows.append(
            (
                sku,
                task_id,
                item.get("product_name"),
                item.get("brand_name"),
                item.get("gen_brand_id"),
                item.get("product_url"),
                price,
                force_decimal(item.get("product_rate")),
                reviews,
                force_int(item.get("merchant_count")),
                monthly_sales,
                force_decimal(item.get("sale_amount")),
                force_int(item.get("amount_abc")),
                force_decimal(item.get("amount_prc")),
                Json(json_safe(preview_image_list)),
                created_dt,
                item.get("category_name"),
                item.get("category_ext_id"),
                force_int(item.get("restrict_type")),
                parse_created_dt(item.get("last_sale_date")),
            )
        )

        calc_rows.append((sku, task_id, Decimal(str(total_score))))

    return raw_rows, calc_rows


def upsert_raw_rows(cur, rows: Sequence[Tuple[Any, ...]]) -> None:
    if not rows:
        return
    _, _, execute_values = load_pg_driver()

    execute_values(
        cur,
        """
        INSERT INTO products_raw_data (
            sku,
            task_id,
            product_name,
            brand_name,
            gen_brand_id,
            product_url,
            sale_price,
            product_rate,
            review_qty,
            merchant_count,
            sale_qty,
            sale_amount,
            amount_abc,
            amount_prc,
            preview_image_list,
            created_dt,
            category_name,
            category_ext_id,
            restrict_type,
            last_sale_date
        ) VALUES %s
        ON CONFLICT (sku) DO UPDATE SET
            task_id = EXCLUDED.task_id,
            product_name = EXCLUDED.product_name,
            brand_name = EXCLUDED.brand_name,
            gen_brand_id = EXCLUDED.gen_brand_id,
            product_url = EXCLUDED.product_url,
            sale_price = EXCLUDED.sale_price,
            product_rate = EXCLUDED.product_rate,
            review_qty = EXCLUDED.review_qty,
            merchant_count = EXCLUDED.merchant_count,
            sale_qty = EXCLUDED.sale_qty,
            sale_amount = EXCLUDED.sale_amount,
            amount_abc = EXCLUDED.amount_abc,
            amount_prc = EXCLUDED.amount_prc,
            preview_image_list = EXCLUDED.preview_image_list,
            created_dt = EXCLUDED.created_dt,
            category_name = EXCLUDED.category_name,
            category_ext_id = EXCLUDED.category_ext_id,
            restrict_type = EXCLUDED.restrict_type,
            last_sale_date = EXCLUDED.last_sale_date
        """,
        rows,
    )


def upsert_calc_rows(cur, rows: Sequence[Tuple[Any, ...]]) -> None:
    if not rows:
        return
    _, _, execute_values = load_pg_driver()

    execute_values(
        cur,
        """
        INSERT INTO products_calculated_metrics (sku, task_id, total_score)
        VALUES %s
        ON CONFLICT (sku) DO UPDATE SET
            task_id = EXCLUDED.task_id,
            total_score = EXCLUDED.total_score,
            updated_at = timezone('utc'::text, now())
        """,
        rows,
    )


def restore_file(cur, path: str) -> RestoreResult:
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    niche_stats = payload.get("niche_stats") or {}
    products = payload.get("products") or []
    trend = payload.get("trend") or []

    final_stats = compute_category_level_stats(niche_stats, products)
    hinted_task_id = task_id_from_path(path)
    task_id, created_task = build_or_update_task(cur, hinted_task_id, final_stats, trend, path)
    raw_rows, calc_rows = build_payloads(task_id, final_stats, products)

    upsert_raw_rows(cur, raw_rows)
    upsert_calc_rows(cur, calc_rows)

    return RestoreResult(
        source_path=path,
        task_id=task_id,
        created_task=created_task,
        raw_count=len(raw_rows),
        calc_count=len(calc_rows),
    )


def main() -> int:
    args = parse_args()
    files = discover_files(args.pattern, args.task_id, args.limit)

    if not files:
        print(f"[INFO] no files matched: {args.pattern}")
        return 0

    print(f"[INFO] matched_files={len(files)}")
    for path in files[:10]:
        print(f"  - {path}")
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more")

    if args.dry_run:
        print("[DRY-RUN] no database changes applied")
        return 0

    restored = 0
    skipped = 0
    failed = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for path in files:
                task_id_hint = task_id_from_path(path)
                if args.only_missing_tasks and task_id_hint and is_valid_uuid(task_id_hint) and task_exists(cur, task_id_hint):
                    skipped += 1
                    print(f"[SKIP] task already exists: {task_id_hint} <- {path}")
                    continue

                try:
                    result = restore_file(cur, path)
                    conn.commit()
                    restored += 1
                    print(
                        "[RESTORED] "
                        f"task_id={result.task_id} "
                        f"created_task={result.created_task} "
                        f"raw={result.raw_count} "
                        f"calc={result.calc_count} "
                        f"path={result.source_path}"
                    )
                except Exception as exc:
                    conn.rollback()
                    failed += 1
                    print(f"[FAILED] path={path} error={exc}")

    print(f"[DONE] restored={restored} skipped={skipped} failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
