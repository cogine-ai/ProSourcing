from core.rpa_db_helpers import (
    products_calculated_metrics_conflict_target,
    products_raw_data_conflict_target,
    resolve_niche_category_id,
)


def test_conflict_targets_match_sku_primary_key_schema():
    assert products_raw_data_conflict_target() == "(sku)"
    assert products_calculated_metrics_conflict_target() == "(sku)"


def test_resolve_niche_category_id_prefers_explicit_id():
    assert resolve_niche_category_id({"category_id": "12345", "category_ext_id": "ext"}) == "12345"


def test_resolve_niche_category_id_falls_back_to_ext_id():
    assert resolve_niche_category_id({"category_ext_id": "01466"}) == "01466"


def test_resolve_niche_category_id_handles_missing():
    assert resolve_niche_category_id({}) is None
    assert resolve_niche_category_id(None) is None
