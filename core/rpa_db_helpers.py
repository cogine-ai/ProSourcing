"""Small helpers for RPA PostgreSQL upserts (kept import-light for unit tests)."""


def resolve_niche_category_id(niche_stats):
    """Algatop niche_stats may expose category_ext_id and/or category_id."""
    if not niche_stats:
        return None
    return niche_stats.get("category_id") or niche_stats.get("category_ext_id")


def products_raw_data_conflict_target():
    """DB schema uses sku as the sole primary key (see data_assets/database_init/init.sql)."""
    return "(sku)"


def products_calculated_metrics_conflict_target():
    return "(sku)"
