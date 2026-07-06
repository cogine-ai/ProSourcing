def resolve_niche_category_id(niche_stats):
    """RPA niche_stats uses category_id; legacy payloads may only have category_ext_id."""
    if not isinstance(niche_stats, dict):
        return None
    return niche_stats.get("category_id") or niche_stats.get("category_ext_id")
