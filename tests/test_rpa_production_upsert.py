import re
from pathlib import Path


def _table_primary_keys(init_sql: str, table_name: str) -> list[str]:
    marker = f"CREATE TABLE IF NOT EXISTS public.{table_name}"
    start = init_sql.find(marker)
    assert start != -1, f"missing table definition for {table_name}"
    end = init_sql.find(");", start)
    assert end != -1, f"missing table terminator for {table_name}"
    body = init_sql[start:end]
    composite_pk = re.search(r"PRIMARY KEY\s*\(([^)]+)\)", body, re.I)
    if composite_pk:
        return [col.strip() for col in composite_pk.group(1).split(",")]

    inline_pk = re.search(r"(\w+)\s+[^,\n]*PRIMARY KEY", body, re.I)
    assert inline_pk, f"missing PRIMARY KEY for {table_name}"
    return [inline_pk.group(1).strip()]


def _on_conflict_target(sql_fragment: str) -> list[str]:
    match = re.search(r"ON CONFLICT\s*\(([^)]+)\)", sql_fragment, re.I)
    assert match, "missing ON CONFLICT target"
    return [col.strip() for col in match.group(1).split(",")]


def test_production_upsert_targets_match_schema_primary_keys():
    init_sql = Path("data_assets/database_init/init.sql").read_text(encoding="utf-8")
    pipeline = Path("core/rpa_final_pipeline.py").read_text(encoding="utf-8")

    raw_sql = pipeline.split('raw_query = """', 1)[1].split('"""', 1)[0]
    calc_sql = pipeline.split('calc_query = "', 1)[1].split('"', 1)[0]

    assert _on_conflict_target(raw_sql) == _table_primary_keys(init_sql, "products_raw_data")
    assert _on_conflict_target(calc_sql) == _table_primary_keys(
        init_sql, "products_calculated_metrics"
    )
