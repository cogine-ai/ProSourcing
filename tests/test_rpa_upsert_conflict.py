import re
from pathlib import Path


PIPELINE_PATH = Path(__file__).resolve().parents[1] / "core" / "rpa_final_pipeline.py"
INIT_SQL_PATH = Path(__file__).resolve().parents[1] / "data_assets" / "database_init" / "init.sql"


def _read_init_sql_primary_keys():
    text = INIT_SQL_PATH.read_text(encoding="utf-8")
    raw_pk = "sku TEXT PRIMARY KEY" in text
    calc_pk = bool(
        re.search(
            r"products_calculated_metrics\s*\([^)]*sku\s+TEXT\s+PRIMARY\s+KEY",
            text,
            re.S,
        )
    )
    return raw_pk, calc_pk


def test_schema_uses_sku_primary_key():
    raw_pk, calc_pk = _read_init_sql_primary_keys()
    assert raw_pk, "products_raw_data should use sku as the sole primary key"
    assert calc_pk, "products_calculated_metrics should reference sku primary key"


def test_production_upsert_matches_sku_primary_key():
    source = PIPELINE_PATH.read_text(encoding="utf-8")
    sync_block = source.split("# 批量同步至数据库", 1)[1]

    assert "ON CONFLICT (sku)" in sync_block
    assert "ON CONFLICT (sku, task_id)" not in sync_block
    assert "task_id = EXCLUDED.task_id" in sync_block


if __name__ == "__main__":
    test_schema_uses_sku_primary_key()
    test_production_upsert_matches_sku_primary_key()
    print("OK: rpa upsert conflict tests passed")
