import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT_SQL = ROOT / "data_assets" / "database_init" / "init.sql"
RPA_PIPELINE = ROOT / "core" / "rpa_final_pipeline.py"


def _extract_primary_key_columns(init_sql: str, table_name: str) -> tuple[str, ...]:
    pattern = rf"CREATE TABLE IF NOT EXISTS public\.{table_name}\s*\((.*?)\);"
    match = re.search(pattern, init_sql, re.DOTALL)
    assert match, f"Could not find table definition for {table_name}"

    for line in match.group(1).splitlines():
        if "PRIMARY KEY" in line.upper():
            pk_match = re.search(r"PRIMARY KEY\s*\(([^)]+)\)", line, re.IGNORECASE)
            if pk_match:
                return tuple(col.strip() for col in pk_match.group(1).split(","))
            pk_match = re.search(r"(\w+)\s+[^,]+PRIMARY KEY", line, re.IGNORECASE)
            if pk_match:
                return (pk_match.group(1),)

    raise AssertionError(f"No PRIMARY KEY found for {table_name}")


def _extract_on_conflict_targets(source: str) -> list[tuple[str, ...]]:
    matches = re.findall(r"ON CONFLICT\s*\(([^)]+)\)", source, re.IGNORECASE)
    return [tuple(col.strip() for col in match.split(",")) for match in matches]


def test_production_upsert_targets_match_schema_primary_keys():
    init_sql = INIT_SQL.read_text(encoding="utf-8")
    pipeline_source = RPA_PIPELINE.read_text(encoding="utf-8")

    raw_pk = _extract_primary_key_columns(init_sql, "products_raw_data")
    calc_pk = _extract_primary_key_columns(init_sql, "products_calculated_metrics")

    conflict_targets = _extract_on_conflict_targets(pipeline_source)
    assert conflict_targets, "Expected ON CONFLICT clauses in rpa_final_pipeline.py"

    for target in conflict_targets:
        assert target in (raw_pk, calc_pk), (
            f"ON CONFLICT {target} does not match schema primary keys "
            f"({raw_pk} or {calc_pk}); PostgreSQL will reject the upsert in production"
        )
