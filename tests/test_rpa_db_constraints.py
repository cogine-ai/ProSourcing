import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT_SQL = ROOT / "data_assets" / "database_init" / "init.sql"
RPA_PIPELINE = ROOT / "core" / "rpa_final_pipeline.py"


def _extract_create_table_block(sql_text, table_name):
    pattern = rf"CREATE TABLE IF NOT EXISTS public\.{table_name}\s*\((.*?)\);"
    match = re.search(pattern, sql_text, flags=re.DOTALL)
    assert match, f"missing CREATE TABLE for {table_name}"
    return match.group(1)


def test_products_tables_use_composite_primary_key():
    sql_text = INIT_SQL.read_text(encoding="utf-8")

    raw_block = _extract_create_table_block(sql_text, "products_raw_data")
    calc_block = _extract_create_table_block(sql_text, "products_calculated_metrics")

    assert "PRIMARY KEY (sku, task_id)" in raw_block
    assert "PRIMARY KEY (sku, task_id)" in calc_block
    assert "FOREIGN KEY (sku, task_id) REFERENCES public.products_raw_data (sku, task_id)" in calc_block


def test_rpa_pipeline_conflict_targets_match_schema():
    pipeline_text = RPA_PIPELINE.read_text(encoding="utf-8")

    assert 'ON CONFLICT (sku, task_id) DO UPDATE' in pipeline_text
    assert pipeline_text.count('ON CONFLICT (sku, task_id) DO UPDATE') >= 2
    assert "raise" in pipeline_text.split("数据库同步失败")[1].split("产生 Excel")[0]
