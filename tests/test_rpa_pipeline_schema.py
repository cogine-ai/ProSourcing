import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT_SQL = ROOT / "data_assets" / "database_init" / "init.sql"
PIPELINE = ROOT / "core" / "rpa_final_pipeline.py"


def _extract_primary_keys(sql_text: str) -> dict[str, tuple[str, ...]]:
    keys: dict[str, tuple[str, ...]] = {}
    for match in re.finditer(
        r"CREATE TABLE IF NOT EXISTS public\.(\w+)\s*\((.*?)\);",
        sql_text,
        flags=re.DOTALL,
    ):
        table = match.group(1)
        body = match.group(2)
        for line in body.splitlines():
            pk_match = re.match(r"\s*(\w+)\s+\w+.*\bPRIMARY KEY\b", line)
            if pk_match:
                keys[table] = (pk_match.group(1),)
                break
    return keys


def _extract_on_conflict_targets(sql_fragment: str) -> tuple[str, ...]:
    match = re.search(r"ON CONFLICT\s*\(([^)]+)\)", sql_fragment, flags=re.IGNORECASE)
    if not match:
        return tuple()
    return tuple(part.strip() for part in match.group(1).split(","))


def test_products_raw_data_on_conflict_matches_schema_primary_key():
    schema = INIT_SQL.read_text(encoding="utf-8")
    pipeline = PIPELINE.read_text(encoding="utf-8")

    primary_keys = _extract_primary_keys(schema)
    assert primary_keys["products_raw_data"] == ("sku",)

    raw_query_match = re.search(
        r'raw_query = """INSERT INTO products_raw_data.*?"""',
        pipeline,
        flags=re.DOTALL,
    )
    assert raw_query_match, "production raw_query not found"

    conflict_cols = _extract_on_conflict_targets(raw_query_match.group(0))
    assert conflict_cols == primary_keys["products_raw_data"]


def test_products_calculated_metrics_on_conflict_matches_schema_primary_key():
    schema = INIT_SQL.read_text(encoding="utf-8")
    pipeline = PIPELINE.read_text(encoding="utf-8")

    primary_keys = _extract_primary_keys(schema)
    assert primary_keys["products_calculated_metrics"] == ("sku",)

    calc_query_match = re.search(
        r'calc_query = "INSERT INTO products_calculated_metrics[^"]+"',
        pipeline,
    )
    assert calc_query_match, "production calc_query not found"

    conflict_cols = _extract_on_conflict_targets(calc_query_match.group(0))
    assert conflict_cols == primary_keys["products_calculated_metrics"]


def test_resolve_niche_category_id_prefers_category_id_then_ext_id():
    def resolve_niche_category_id(niche_stats):
        return niche_stats.get("category_id") or niche_stats.get("category_ext_id")

    assert resolve_niche_category_id({"category_id": "12345"}) == "12345"
    assert resolve_niche_category_id({"category_ext_id": "67890"}) == "67890"
    assert resolve_niche_category_id(
        {"category_id": "12345", "category_ext_id": "67890"}
    ) == "12345"
    assert resolve_niche_category_id({}) is None
