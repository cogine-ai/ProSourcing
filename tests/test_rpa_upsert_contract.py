import importlib.util
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "rpa_final_pipeline.py"


def _load_rpa_module():
    for name in (
        "openpyxl",
        "openpyxl.drawing.image",
        "supabase",
        "dotenv",
        "psycopg2",
        "psycopg2.extras",
    ):
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)

    openpyxl = sys.modules["openpyxl"]
    openpyxl.load_workbook = MagicMock()
    sys.modules["openpyxl.drawing.image"].Image = MagicMock()

    dotenv = sys.modules["dotenv"]
    dotenv.load_dotenv = MagicMock()

    supabase = sys.modules["supabase"]
    supabase.create_client = MagicMock(return_value=MagicMock())
    supabase.Client = MagicMock()

    psycopg2 = sys.modules["psycopg2"]
    psycopg2.connect = MagicMock(return_value=MagicMock())
    sys.modules["psycopg2.extras"].execute_values = MagicMock()

    scoring = types.ModuleType("core.scoring")
    scoring.ScoringEngine = MagicMock()
    sys.modules["core.scoring"] = scoring

    os.environ["ENV_MOD"] = "production"

    spec = importlib.util.spec_from_file_location("rpa_final_pipeline", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["rpa_final_pipeline"] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_niche_category_id_prefers_category_id():
    module = _load_rpa_module()
    niche_stats = {"category_id": "00042", "category_ext_id": "99999"}
    assert module._resolve_niche_category_id(niche_stats) == "00042"


def test_resolve_niche_category_id_falls_back_to_category_ext_id():
    module = _load_rpa_module()
    niche_stats = {"category_ext_id": "00042"}
    assert module._resolve_niche_category_id(niche_stats) == "00042"


def test_build_products_raw_upsert_sql_for_sku_primary_key():
    module = _load_rpa_module()
    sql = module._build_products_raw_upsert_sql("(sku)")
    assert "ON CONFLICT (sku) DO UPDATE SET" in sql
    assert "task_id = EXCLUDED.task_id" in sql
    assert "sale_qty = EXCLUDED.sale_qty" in sql


def test_build_products_raw_upsert_sql_for_composite_primary_key():
    module = _load_rpa_module()
    sql = module._build_products_raw_upsert_sql("(sku, task_id)")
    assert "ON CONFLICT (sku, task_id) DO UPDATE SET" in sql
    assert "task_id = EXCLUDED.task_id" not in sql


def test_build_products_calc_upsert_sql_for_sku_primary_key():
    module = _load_rpa_module()
    sql = module._build_products_calc_upsert_sql("(sku)")
    assert "ON CONFLICT (sku) DO UPDATE SET" in sql
    assert "task_id = EXCLUDED.task_id" in sql
    assert "total_score = EXCLUDED.total_score" in sql


def test_get_products_conflict_target_detects_composite_pk():
    module = _load_rpa_module()
    module._products_conflict_target_cache = None
    cursor = MagicMock()
    cursor.fetchone.return_value = (["sku", "task_id"],)
    assert module._get_products_conflict_target(cursor) == "(sku, task_id)"


def test_get_products_conflict_target_defaults_to_sku_pk():
    module = _load_rpa_module()
    module._products_conflict_target_cache = None
    cursor = MagicMock()
    cursor.fetchone.return_value = (["sku"],)
    assert module._get_products_conflict_target(cursor) == "(sku)"
