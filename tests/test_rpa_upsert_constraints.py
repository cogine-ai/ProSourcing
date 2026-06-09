import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INIT_SQL = REPO_ROOT / "data_assets" / "database_init" / "init.sql"
PIPELINE_PY = REPO_ROOT / "core" / "rpa_final_pipeline.py"


def _primary_key_columns(init_sql: str, table_name: str) -> tuple[str, ...]:
    pattern = rf"CREATE TABLE IF NOT EXISTS public\.{table_name}\s*\((.*?)\);"
    match = re.search(pattern, init_sql, re.DOTALL | re.IGNORECASE)
    assert match, f"table definition not found: {table_name}"

    body = match.group(1)
    composite = re.search(r"PRIMARY KEY\s*\(([^)]+)\)", body, re.IGNORECASE)
    if composite:
        return tuple(col.strip() for col in composite.group(1).split(","))

    inline = re.findall(r"(\w+)\s+\w+(?:\s+PRIMARY KEY)", body, re.IGNORECASE)
    if inline:
        return tuple(inline)

    raise AssertionError(f"PRIMARY KEY not found for table: {table_name}")


def _on_conflict_columns(pipeline_source: str, table_name: str) -> tuple[str, ...]:
    pattern = rf"INSERT INTO {table_name}.*?ON CONFLICT \(([^)]+)\)"
    match = re.search(pattern, pipeline_source, re.DOTALL | re.IGNORECASE)
    assert match, f"ON CONFLICT clause not found for table: {table_name}"
    return tuple(col.strip() for col in match.group(1).split(","))


def test_rpa_production_upsert_matches_schema_primary_keys():
    init_sql = INIT_SQL.read_text(encoding="utf-8")
    pipeline_source = PIPELINE_PY.read_text(encoding="utf-8")

    for table in ("products_raw_data", "products_calculated_metrics"):
        pk_cols = _primary_key_columns(init_sql, table)
        conflict_cols = _on_conflict_columns(pipeline_source, table)
        assert conflict_cols == pk_cols, (
            f"{table}: ON CONFLICT {conflict_cols} does not match schema PRIMARY KEY {pk_cols}"
        )
