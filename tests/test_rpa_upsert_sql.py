"""Regression: production upsert ON CONFLICT must match init.sql primary keys."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT_SQL = ROOT / "data_assets" / "database_init" / "init.sql"
PIPELINE = ROOT / "core" / "rpa_final_pipeline.py"


def _table_primary_key_columns(sql_text: str, table_name: str) -> tuple[str, ...]:
    pattern = rf"CREATE TABLE IF NOT EXISTS public\.{table_name}\s*\((.*?)\);"
    match = re.search(pattern, sql_text, re.DOTALL)
    assert match, f"missing CREATE TABLE for {table_name}"
    body = match.group(1)
    for line in body.splitlines():
        line = line.strip().rstrip(",")
        composite = re.search(r"PRIMARY KEY\s*\(([^)]+)\)", line, re.IGNORECASE)
        if composite:
            return tuple(c.strip() for c in composite.group(1).split(","))
        inline = re.match(r"(\w+)\s+\w+.*\bPRIMARY KEY\b", line, re.IGNORECASE)
        if inline:
            return (inline.group(1),)
    raise AssertionError(f"no PRIMARY KEY found for {table_name}")


def _on_conflict_columns(query: str) -> tuple[str, ...]:
    match = re.search(r"ON CONFLICT\s*\(([^)]+)\)", query, re.IGNORECASE)
    assert match, "ON CONFLICT clause missing"
    return tuple(c.strip() for c in match.group(1).split(","))


def test_production_upsert_matches_schema_primary_keys():
    schema = INIT_SQL.read_text(encoding="utf-8")
    pipeline = PIPELINE.read_text(encoding="utf-8")

    raw_pk = _table_primary_key_columns(schema, "products_raw_data")
    calc_pk = _table_primary_key_columns(schema, "products_calculated_metrics")

    raw_queries = re.findall(
        r'raw_query\s*=\s*"""(.*?)"""',
        pipeline,
        re.DOTALL,
    )
    calc_queries = re.findall(
        r'calc_query\s*=\s*"([^"]+)"',
        pipeline,
    )

    assert raw_queries, "expected raw_query upsert SQL in rpa_final_pipeline"
    assert calc_queries, "expected calc_query upsert SQL in rpa_final_pipeline"

    assert _on_conflict_columns(raw_queries[0]) == raw_pk
    assert _on_conflict_columns(calc_queries[0]) == calc_pk
