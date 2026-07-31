def resolve_niche_category_id(niche_stats):
    """Algatop niche stats may expose category_id or category_ext_id depending on API version."""
    if not niche_stats:
        return None
    return niche_stats.get("category_id") or niche_stats.get("category_ext_id")
