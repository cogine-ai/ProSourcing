import json
import re
from pathlib import Path

from core.rpa_sync_utils import (
    resolve_niche_category_id,
    serialize_preview_image_list,
)


def test_resolve_niche_category_id_prefers_category_id():
    assert resolve_niche_category_id({"category_id": "01466", "category_ext_id": "Pet goods"}) == "01466"


def test_resolve_niche_category_id_falls_back_to_ext_id():
    assert resolve_niche_category_id({"category_ext_id": "01466"}) == "01466"


def test_serialize_preview_image_list_encodes_objects():
    payload = [{"medium": "https://example.com/a.jpg"}]
    assert json.loads(serialize_preview_image_list(payload)) == payload


def test_production_upsert_matches_schema_primary_keys():
    pipeline_source = Path("core/rpa_final_pipeline.py").read_text(encoding="utf-8")
    init_sql = Path("data_assets/database_init/init.sql").read_text(encoding="utf-8")

    assert "ON CONFLICT (sku, task_id)" not in pipeline_source
    assert re.search(r"products_raw_data[\s\S]*?ON CONFLICT \(sku\)", pipeline_source)
    assert re.search(r"products_calculated_metrics[\s\S]*?ON CONFLICT \(sku\)", pipeline_source)
    assert "sku TEXT PRIMARY KEY" in init_sql
