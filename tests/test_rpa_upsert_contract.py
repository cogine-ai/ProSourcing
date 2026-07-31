import os
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("ENV_MOD", "test")

sys.modules.setdefault("pandas", MagicMock())

with patch("supabase.create_client", return_value=MagicMock()):
    from core.rpa_final_pipeline import (
        _build_calc_upsert_sql,
        _build_raw_upsert_sql,
        _resolve_niche_category_id,
    )


def test_resolve_niche_category_id_prefers_category_id():
    assert _resolve_niche_category_id({"category_id": "12345", "category_ext_id": "ext"}) == "12345"


def test_resolve_niche_category_id_falls_back_to_category_ext_id():
    assert _resolve_niche_category_id({"category_ext_id": "ext-99"}) == "ext-99"


def test_resolve_niche_category_id_returns_none_when_missing():
    assert _resolve_niche_category_id({}) is None
    assert _resolve_niche_category_id(None) is None


def test_raw_upsert_sql_matches_sku_only_primary_key():
    sql = _build_raw_upsert_sql(("sku",))
    assert "ON CONFLICT (sku) DO UPDATE SET" in sql
    assert "task_id = EXCLUDED.task_id" in sql
    assert "ON CONFLICT (sku, task_id)" not in sql


def test_raw_upsert_sql_matches_composite_primary_key():
    sql = _build_raw_upsert_sql(("sku", "task_id"))
    assert "ON CONFLICT (sku, task_id) DO UPDATE SET" in sql
    assert "task_id = EXCLUDED.task_id" not in sql


def test_calc_upsert_sql_matches_sku_only_primary_key():
    sql = _build_calc_upsert_sql(("sku",))
    assert "ON CONFLICT (sku) DO UPDATE SET task_id = EXCLUDED.task_id, total_score = EXCLUDED.total_score" in sql


def test_calc_upsert_sql_matches_composite_primary_key():
    sql = _build_calc_upsert_sql(("sku", "task_id"))
    assert "ON CONFLICT (sku, task_id) DO UPDATE SET total_score = EXCLUDED.total_score" in sql


def test_init_sql_products_primary_key_is_sku_only():
    init_sql = Path("data_assets/database_init/init.sql").read_text(encoding="utf-8")
    raw_table_match = re.search(
        r"CREATE TABLE IF NOT EXISTS public\.products_raw_data \((.*?)\);",
        init_sql,
        re.DOTALL,
    )
    assert raw_table_match is not None
    assert "sku TEXT PRIMARY KEY" in raw_table_match.group(1)
    assert "PRIMARY KEY (sku, task_id)" not in raw_table_match.group(1)
