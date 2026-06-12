import json


def resolve_niche_category_id(niche_stats):
    """Algatop niche_stats may expose category_id or category_ext_id."""
    if not niche_stats:
        return None
    return niche_stats.get("category_id") or niche_stats.get("category_ext_id")


def serialize_preview_image_list(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)
