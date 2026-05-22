from pathlib import Path


def test_production_upsert_matches_sku_primary_key():
    """Production Postgres schema defines sku as the sole primary key."""
    src = Path(__file__).resolve().parents[1] / "core" / "rpa_final_pipeline.py"
    text = src.read_text(encoding="utf-8")

    assert "ON CONFLICT (sku, task_id)" not in text
    assert "ON CONFLICT (sku) DO UPDATE SET task_id = EXCLUDED.task_id" in text
    assert "INSERT INTO products_calculated_metrics (sku, task_id, total_score)" in text
    assert "ON CONFLICT (sku) DO UPDATE SET task_id = EXCLUDED.task_id, total_score" in text


def test_task_category_id_resolver_covers_both_fields():
    from core.rpa_final_pipeline import _resolve_task_category_id

    assert _resolve_task_category_id({"category_id": "12345"}) == "12345"
    assert _resolve_task_category_id({"category_ext_id": "99"}) == "99"
    assert _resolve_task_category_id({"category_id": "1", "category_ext_id": "2"}) == "1"
