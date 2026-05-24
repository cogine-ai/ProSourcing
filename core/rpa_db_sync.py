"""Helpers for RPA PostgreSQL upserts (kept dependency-free for unit tests)."""


def resolve_niche_category_id(niche_stats):
    """Algatop niche stats may expose category_id or category_ext_id depending on API version."""
    if not niche_stats:
        return None
    for key in ("category_id", "category_ext_id", "categoryId", "categoryExtId"):
        value = niche_stats.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def format_product_upsert_conflict_target(pk_columns):
    """Build ON CONFLICT target matching the live products_raw_data primary key."""
    cols = tuple(pk_columns or ())
    if cols == ("sku", "task_id"):
        return "(sku, task_id)"
    return "(sku)"


def lookup_table_upsert_conflict_target(cursor, table_name):
    """Detect a table's primary key columns from PostgreSQL catalog."""
    cursor.execute(
        """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a
          ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = (%s)::regclass
          AND i.indisprimary
        ORDER BY array_position(i.indkey::smallint[], a.attnum::smallint)
        """,
        (f"public.{table_name}",),
    )
    columns = [row[0] for row in cursor.fetchall()]
    return format_product_upsert_conflict_target(columns)
