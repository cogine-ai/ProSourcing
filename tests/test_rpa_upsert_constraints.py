"""Ensure production RPA upsert SQL matches PostgreSQL primary-key constraints."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INIT_SQL = REPO_ROOT / "data_assets" / "database_init" / "init.sql"
PIPELINE_PY = REPO_ROOT / "core" / "rpa_final_pipeline.py"


def _table_primary_key(table_name: str, sql_text: str) -> str | None:
    pattern = rf"CREATE TABLE IF NOT EXISTS public\.{table_name}\s*\(\s*(\w+)\s+TEXT PRIMARY KEY"
    match = re.search(pattern, sql_text, re.IGNORECASE)
    return match.group(1) if match else None


def _extract_on_conflict_targets(sql_fragment: str) -> list[str]:
    return re.findall(r"ON CONFLICT\s*\(([^)]+)\)", sql_fragment, re.IGNORECASE)


def test_products_tables_use_sku_primary_key():
    sql_text = INIT_SQL.read_text(encoding="utf-8")
    assert _table_primary_key("products_raw_data", sql_text) == "sku"
    assert _table_primary_key("products_calculated_metrics", sql_text) == "sku"


def test_production_upsert_targets_sku_only():
    pipeline_text = PIPELINE_PY.read_text(encoding="utf-8")
    marker = 'print(f"[SYNC] 正在同步 {len(raw_payloads)} 条数据至本地 PostgreSQL...")'
    production_block = pipeline_text.split(marker, 1)[1]

    conflict_targets = _extract_on_conflict_targets(production_block)
    assert conflict_targets, "expected production upsert ON CONFLICT clauses"

    for target in conflict_targets:
        columns = [col.strip() for col in target.split(",")]
        assert columns == ["sku"], (
            f"ON CONFLICT ({target}) has no matching unique constraint; "
            "schema defines PRIMARY KEY (sku) only"
        )


if __name__ == "__main__":
    test_products_tables_use_sku_primary_key()
    test_production_upsert_targets_sku_only()
    print("All tests passed")
