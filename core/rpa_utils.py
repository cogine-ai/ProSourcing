def resolve_niche_category_id(niche_stats):
    """Algatop niche_stats 通常提供 category_ext_id；部分版本也有 category_id。"""
    if not niche_stats:
        return None
    return niche_stats.get("category_id") or niche_stats.get("category_ext_id")
