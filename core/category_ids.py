def resolve_niche_category_id(niche_stats):
    """Algatop niche stats may expose category_id, category_ext_id, or category_code."""
    if not niche_stats:
        return None
    for key in ("category_id", "category_ext_id", "category_code"):
        value = niche_stats.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None
