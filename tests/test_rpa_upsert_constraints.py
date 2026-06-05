import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_production_upsert_targets_composite_primary_key():
  pipeline = _read("core/rpa_final_pipeline.py")
  init_sql = _read("data_assets/database_init/init.sql")

  conflict_targets = re.findall(r"ON CONFLICT \(([^)]+)\)", pipeline)
  assert conflict_targets, "expected production upsert ON CONFLICT clauses"
  assert all(target.strip() == "sku, task_id" for target in conflict_targets)

  normalized_init = " ".join(init_sql.split())
  assert "PRIMARY KEY (sku, task_id)" in normalized_init
  assert normalized_init.count("PRIMARY KEY (sku, task_id)") >= 2


def test_migration_script_aligns_with_production_upsert():
  migration = _read("scripts/sql/migrate_products_composite_pk.sql")
  assert "PRIMARY KEY (sku, task_id)" in migration
  assert "products_calculated_metrics_sku_task_fkey" in migration
