"""Schema contract tests for per-task product upserts."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT_SQL = ROOT / "data_assets" / "database_init" / "init.sql"
MIGRATION_SQL = ROOT / "data_assets" / "database_init" / "migrate_products_composite_pk.sql"
RPA_PIPELINE = ROOT / "core" / "rpa_final_pipeline.py"
FINAL_PIPELINE = ROOT / "core" / "final_pipeline.py"


def test_init_sql_declares_composite_primary_keys():
    text = INIT_SQL.read_text(encoding="utf-8")
    assert "PRIMARY KEY (sku, task_id)" in text
    assert re.search(r"products_raw_data\s*\([^;]*sku TEXT PRIMARY KEY", text, re.S) is None


def test_migration_script_targets_composite_primary_keys():
    text = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "products_raw_data_pkey PRIMARY KEY (sku, task_id)" in text
    assert "products_calculated_metrics_pkey PRIMARY KEY (sku, task_id)" in text


def test_rpa_pipeline_uses_composite_on_conflict():
    text = RPA_PIPELINE.read_text(encoding="utf-8")
    assert "ON CONFLICT (sku, task_id)" in text


def test_pg_shim_upsert_uses_composite_key_for_product_tables():
    text = FINAL_PIPELINE.read_text(encoding="utf-8")
    assert "pk = 'sku, task_id'" in text
    assert "'products_raw_data', 'products_calculated_metrics'" in text
