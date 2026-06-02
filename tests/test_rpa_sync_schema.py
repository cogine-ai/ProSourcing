from pathlib import Path


def test_init_schema_matches_rpa_upsert_conflict_target():
    init_sql = Path("data_assets/database_init/init.sql").read_text(encoding="utf-8")
    pipeline_py = Path("core/rpa_final_pipeline.py").read_text(encoding="utf-8")

    assert "PRIMARY KEY (sku, task_id)" in init_sql
    assert "ON CONFLICT (sku, task_id)" in pipeline_py


def test_migration_script_exists_for_existing_databases():
    migration = Path("scripts/sql/migrate_products_composite_unique.sql")
    assert migration.is_file()
    sql = migration.read_text(encoding="utf-8")
    assert "products_raw_data_pkey PRIMARY KEY (sku, task_id)" in sql
