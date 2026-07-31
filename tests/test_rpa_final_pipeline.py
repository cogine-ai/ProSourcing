from pathlib import Path


def _load_pipeline_helpers():
    namespace = {}
    source_path = Path(__file__).resolve().parents[1] / "core" / "rpa_final_pipeline.py"
    source = source_path.read_text(encoding="utf-8")
    start = source.index("def resolve_niche_category_id")
    end = source.index("\ndef json_safe")
    exec(source[start:end], namespace)
    return namespace["resolve_niche_category_id"]


resolve_niche_category_id = _load_pipeline_helpers()
PIPELINE_SOURCE = (Path(__file__).resolve().parents[1] / "core" / "rpa_final_pipeline.py").read_text(encoding="utf-8")


def test_resolve_niche_category_id_prefers_category_id():
    assert resolve_niche_category_id({"category_id": "01466", "category_ext_id": "99999"}) == "01466"


def test_resolve_niche_category_id_falls_back_to_category_ext_id():
    assert resolve_niche_category_id({"category_ext_id": "01466"}) == "01466"


def test_resolve_niche_category_id_handles_missing_values():
    assert resolve_niche_category_id({}) is None
    assert resolve_niche_category_id(None) is None


def test_production_upsert_sql_matches_sku_primary_key_schema():
    assert "PRODUCTION_RAW_UPSERT_SQL" in PIPELINE_SOURCE
    assert "ON CONFLICT (sku) DO UPDATE" in PIPELINE_SOURCE
    assert "ON CONFLICT (sku, task_id)" not in PIPELINE_SOURCE
