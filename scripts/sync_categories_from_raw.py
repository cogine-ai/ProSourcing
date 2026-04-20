import json
import os

import psycopg2
from psycopg2.extras import execute_values


def find_first_existing(candidates):
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


TOP_TITLE_ALIASES = {
    "красота, здоровье": "красота и здоровье",
}

TOP_CATEGORY_CODE_MAP = {
    "Smartphones and gadgets": "00002",
    "Computers": "00005",
    "TV_Audio": "00012",
    "Home equipment": "00034",
    "Car goods": "00079",
    "Child goods": "00083",
    "Leisure": "00147",
    "Furniture": "00239",
    "Home": "00240",
    "Beauty care": "00299",
    "Fashion accessories": "00751",
    "Construction and repair": "00754",
    "Shoes": "00791",
    "Sports and outdoors": "00864",
    "Fashion": "00933",
    "Pet goods": "01466",
    "Office and school supplies": "02062",
    "Gifts and party supplies": "02605",
    "Pharmacy": "02807",
    "Jewelry and Bijouterie": "06498",
}


def find_master_file():
    return find_first_existing(
        [
            "/app/scripts/full_category_data.json",
            "scripts/full_category_data.json",
            "full_category_data.json",
        ]
    )


def find_full_tree_file():
    return find_first_existing(
        [
            "/app/scripts/kaspi_full_tree_raw.json",
            "scripts/kaspi_full_tree_raw.json",
            "kaspi_full_tree_raw.json",
        ]
    )


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def extract_list(payload):
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        if isinstance(payload.get("master"), list):
            return payload["master"]

        for value in payload.values():
            if isinstance(value, list) and len(value) > 10:
                return value

    return []


def column_exists(cur, table_name, column_name):
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return cur.fetchone() is not None


def build_master_top_name_map(master_payload):
    top_map = {}
    id_map = {}
    for item in extract_list(master_payload):
        if not isinstance(item, dict) or item.get("level") != 1:
            continue
        name_ru = str(item.get("name_ru") or "").strip()
        algatop_id = str(item.get("algatop_id") or "").strip()
        if not name_ru:
            continue
        key = " ".join(name_ru.replace("<br/>", " ").replace("<br />", " ").split()).strip().lower()
        top_map[key] = {
            "algatop_id": algatop_id,
            "name_ru": name_ru,
            "name_cn": item.get("name_cn"),
            "name_en": item.get("name_en"),
        }
        if algatop_id:
            id_map[algatop_id] = top_map[key]

    for alias_key, target_key in TOP_TITLE_ALIASES.items():
        mapped = top_map.get(target_key)
        if mapped:
            top_map[alias_key] = mapped
    return top_map, id_map


def build_master_name_map(master_payload):
    grouped = {}
    for item in extract_list(master_payload):
        if not isinstance(item, dict):
            continue
        name_ru = str(item.get("name_ru") or "").strip()
        if not name_ru:
            continue
        key = " ".join(name_ru.replace("<br/>", " ").replace("<br />", " ").split()).strip().lower()
        grouped.setdefault(key, []).append(
            {
                "algatop_id": str(item.get("algatop_id") or "").strip(),
                "name_ru": name_ru,
                "name_cn": item.get("name_cn"),
                "name_en": item.get("name_en"),
            }
        )

    return {key: items[0] for key, items in grouped.items() if len(items) == 1}


def flatten_full_tree(root_payload, master_payload):
    rows = []
    top_map, id_map = build_master_top_name_map(master_payload)
    master_name_map = build_master_name_map(master_payload)

    def walk(node, parent_id=None, is_top_level=False):
        category_id = str(node.get("code") or node.get("id") or "").strip()
        if not category_id:
            return 0

        title = (node.get("title") or node.get("name") or "").strip()
        title_key = " ".join(title.replace("<br/>", " ").replace("<br />", " ").split()).strip().lower()
        mapped_top = None
        matched_node = None
        if is_top_level:
            mapped_algatop_id = TOP_CATEGORY_CODE_MAP.get(category_id)
            if mapped_algatop_id:
                mapped_top = id_map.get(mapped_algatop_id)
            if not mapped_top:
                mapped_top = top_map.get(title_key)
            matched_node = mapped_top
        else:
            matched_node = master_name_map.get(title_key)
        children = node.get("subNodes") or node.get("children") or []
        leaf_count = 0

        for child in children:
            leaf_count += walk(child, category_id, False)

        is_leaf = len(children) == 0
        if is_leaf:
            leaf_count = 1

        rows.append(
            {
                "category_id": category_id,
                "category_name": title,
                "parent_category_id": parent_id,
                "monthly_sales": 0,
                "sale_product_qty": 0,
                "sale_qty": 0,
                "leaf_count": leaf_count if is_top_level else 0,
                "algatop_id": matched_node.get("algatop_id") if matched_node else category_id,
                "name_ru": matched_node.get("name_ru") if matched_node else title,
                "name_cn": matched_node.get("name_cn") if matched_node else None,
                "name_en": matched_node.get("name_en") if matched_node else None,
                "level": node.get("level"),
                "is_leaf": is_leaf,
                "is_top_level": is_top_level,
                "is_has_subcategory": 0 if is_leaf else 1,
            }
        )

        return leaf_count

    top_nodes = root_payload.get("subNodes") or root_payload.get("children") or []
    for node in top_nodes:
        walk(node, None, True)

    return rows


def sync_categories_from_full_tree(cur, full_tree_payload, master_payload):
    rows = flatten_full_tree(full_tree_payload, master_payload)
    if not rows:
        raise RuntimeError("Full tree payload is empty.")

    has_is_has_subcategory = column_exists(cur, "categories", "is_has_subcategory")
    has_is_top_level = column_exists(cur, "categories", "is_top_level")

    columns = [
        "category_id",
        "category_name",
        "parent_category_id",
        "monthly_sales",
        "sale_product_qty",
        "sale_qty",
        "leaf_count",
        "algatop_id",
        "name_ru",
        "name_cn",
        "name_en",
        "level",
        "is_leaf",
    ]
    if has_is_top_level:
        columns.append("is_top_level")
    if has_is_has_subcategory:
        columns.append("is_has_subcategory")

    values = [tuple(row.get(column) for column in columns) for row in rows]

    cur.execute("TRUNCATE TABLE categories CASCADE;")
    execute_values(
        cur,
        f"""
        INSERT INTO categories ({", ".join(columns)})
        VALUES %s
        """,
        values,
    )
    return len(rows)


def main():
    master_file = find_master_file()
    full_tree_file = find_full_tree_file()
    if not master_file:
        raise RuntimeError("full_category_data.json was not found.")
    if not full_tree_file:
        raise RuntimeError("kaspi_full_tree_raw.json was not found.")

    master_payload = load_json(master_file)
    full_tree_payload = load_json(full_tree_file)
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:prosourcing123@db:5432/prosourcing",
    )

    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            synced = sync_categories_from_full_tree(cur, full_tree_payload, master_payload)
        conn.commit()

    print(f"[DONE] Synced categories from raw tree: {synced}")


if __name__ == "__main__":
    main()
