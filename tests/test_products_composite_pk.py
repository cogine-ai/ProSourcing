"""Schema and upsert alignment for per-task product rows."""

from pathlib import Path


def test_init_sql_uses_composite_primary_key():
    init_sql = Path(__file__).resolve().parents[1] / "data_assets" / "database_init" / "init.sql"
    text = init_sql.read_text(encoding="utf-8")

    raw_start = text.index("CREATE TABLE IF NOT EXISTS public.products_raw_data")
    raw_block = text[raw_start:text.index("CREATE TABLE IF NOT EXISTS public.products_calculated_metrics")]
    assert "PRIMARY KEY (sku, task_id)" in raw_block

    calc_start = text.index("CREATE TABLE IF NOT EXISTS public.products_calculated_metrics")
    calc_block = text[calc_start:text.index("CREATE TABLE IF NOT EXISTS public.analysis_tasks")]
    assert "PRIMARY KEY (sku, task_id)" in calc_block
    assert "REFERENCES public.products_raw_data (sku, task_id)" in calc_block


def test_rpa_pipeline_upsert_matches_composite_key():
    pipeline = Path(__file__).resolve().parents[1] / "core" / "rpa_final_pipeline.py"
    text = pipeline.read_text(encoding="utf-8")

    assert "ON CONFLICT (sku, task_id)" in text
    assert "ON CONFLICT (sku) DO UPDATE SET task_id" not in text
