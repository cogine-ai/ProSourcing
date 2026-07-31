from core.rpa_utils import resolve_niche_category_id


def test_resolve_niche_category_id_prefers_category_id():
    assert resolve_niche_category_id({"category_id": "123", "category_ext_id": "999"}) == "123"


def test_resolve_niche_category_id_falls_back_to_ext_id():
    assert resolve_niche_category_id({"category_ext_id": "04456"}) == "04456"


def test_resolve_niche_category_id_empty():
    assert resolve_niche_category_id({}) is None
    assert resolve_niche_category_id(None) is None
