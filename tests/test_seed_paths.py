import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_category_seed_file():
    candidates = [
        os.path.join(PROJECT_ROOT, "data_assets", "category_trees", "full_category_data.json"),
        os.path.join(PROJECT_ROOT, "scripts", "full_category_data.json"),
        "/app/data_assets/category_trees/full_category_data.json",
        "/app/scripts/full_category_data.json",
        "data_assets/category_trees/full_category_data.json",
        "scripts/full_category_data.json",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def test_resolve_category_seed_file_points_at_existing_asset():
    seed_file = _resolve_category_seed_file()
    assert seed_file is not None
    assert os.path.exists(seed_file)
    assert seed_file.endswith("full_category_data.json")

    with open(seed_file, "r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)

    assert payload.get("master")
    assert payload.get("stats")


def test_legacy_seed_path_is_missing():
    legacy = os.path.join(PROJECT_ROOT, "scripts", "full_category_data.json")
    assert not os.path.exists(legacy)
