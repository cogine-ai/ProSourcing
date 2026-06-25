import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
INIT_SQL = ROOT / "data_assets" / "database_init" / "init.sql"
MIGRATION_SQL = ROOT / "scripts" / "sql" / "migrate_composite_sku_task_pk.sql"
PIPELINE_PY = ROOT / "core" / "rpa_final_pipeline.py"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_init_schema_declares_composite_primary_key():
  sql = _read(INIT_SQL)
  assert "PRIMARY KEY (sku, task_id)" in sql
  assert re.search(r"CREATE TABLE IF NOT EXISTS public\.products_raw_data[\s\S]*?PRIMARY KEY \(sku, task_id\)", sql)
  assert re.search(r"CREATE TABLE IF NOT EXISTS public\.products_calculated_metrics[\s\S]*?PRIMARY KEY \(sku, task_id\)", sql)


def test_migration_script_targets_composite_primary_key():
  sql = _read(MIGRATION_SQL)
  assert "PRIMARY KEY (sku, task_id)" in sql
  assert "products_raw_data_pkey" in sql
  assert "products_calculated_metrics_pkey" in sql


def test_rpa_pipeline_upsert_matches_composite_key():
  source = _read(PIPELINE_PY)
  assert "ON CONFLICT (sku, task_id)" in source
  assert 'on_conflict="sku,task_id"' in source


def test_analysis_tasks_defined_before_product_tables():
  sql = _read(INIT_SQL)
  tasks_pos = sql.index("CREATE TABLE IF NOT EXISTS public.analysis_tasks")
  raw_pos = sql.index("CREATE TABLE IF NOT EXISTS public.products_raw_data")
  assert tasks_pos < raw_pos
