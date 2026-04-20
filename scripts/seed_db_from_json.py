import json
import os
import psycopg2
from psycopg2.extras import execute_values

VERIFIED_TOP_CATEGORY_COUNTS = {
    "00933": 1939806, "00299": 493504, "00751": 772686, "00240": 1565665,
    "06498": 1058193, "00083": 333258, "00002": 1484102, "02807": 100437,
    "00079": 1377666, "02605": 247301, "00791": 522075, "00147": 437012,
    "00239": 547487, "00754": 533712, "00005": 365904, "00864": 395022,
    "02062": 126858, "00034": 101593, "01793": 23144, "00012": 62256,
    "01466": 85313,
}

def find_master_file():
    candidates = ["/app/scripts/full_category_data.json", "scripts/full_category_data.json", "full_category_data.json"]
    for p in candidates:
        if os.path.exists(p): return p
    return None

def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as fh: return json.load(fh)

def normalize_text(v):
    return " ".join(str(v or "").split()).strip()

def seed_db():
    print("[ProSourcing] Starting FORCE SEED process (v2)...")
    master_file = find_master_file()
    if not master_file: raise RuntimeError("full_category_data.json not found")
    data = load_json(master_file)
    master_list = data.get('master', [])
    stats_list = data.get('stats', [])

    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:prosourcing123@db:5432/prosourcing")
    
    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            # 1. Seed Master Table
            print(f"Truncating and seeding master table ({len(master_list)} rows)...")
            cur.execute("TRUNCATE TABLE algatop_categories_master CASCADE;")
            m_rows = []
            for item in master_list:
                m_rows.append((
                    str(item.get("algatop_id") or "").strip(),
                    normalize_text(item.get("name_ru")),
                    normalize_text(item.get("name_cn")),
                    normalize_text(item.get("name_en")),
                    str(item.get("parent_id") or "").strip() or None,
                    item.get("level"),
                    bool(item.get("is_leaf", False)),
                    item.get("monthly_sales", 0)
                ))
            execute_values(cur, "INSERT INTO algatop_categories_master (algatop_id, name_ru, name_cn, name_en, parent_id, level, is_leaf, monthly_sales) VALUES %s", m_rows)

            # 2. Seed Categories Table (强制包含 is_top_level)
            print(f"Truncating and seeding categories table...")
            cur.execute("TRUNCATE TABLE categories CASCADE;")
            c_rows = []
            for item in master_list:
                ru = normalize_text(item.get("name_ru"))
                cn = normalize_text(item.get("name_cn"))
                c_rows.append((
                    str(item.get("algatop_id") or "").strip(),
                    cn or ru,
                    str(item.get("parent_id") or "").strip() or None,
                    item.get("monthly_sales", 0),
                    str(item.get("algatop_id") or "").strip(),
                    ru, cn or None,
                    item.get("level"),
                    bool(item.get("is_leaf", False)),
                    item.get("level") == 1, # is_top_level
                    0 if item.get("is_leaf") else 1 # is_has_subcategory
                ))
            execute_values(cur, """
                INSERT INTO categories 
                (category_id, category_name, parent_category_id, monthly_sales, algatop_id, name_ru, name_cn, level, is_leaf, is_top_level, is_has_subcategory)
                VALUES %s
            """, c_rows)

            # 3. Seed Stats
            print(f"Seeding stats table ({len(stats_list)} rows)...")
            cur.execute("TRUNCATE TABLE algatop_top_category_stats CASCADE;")
            s_rows = []
            for item in stats_list:
                s_rows.append((
                    str(item.get("algatop_id") or "").strip(),
                    item.get("sales_qty", 0), item.get("revenue", 0),
                    item.get("product_count", 0), item.get("seller_count", 0), item.get("brand_count", 0)
                ))
            execute_values(cur, "INSERT INTO algatop_top_category_stats (algatop_id, sales_qty, revenue, product_count, seller_count, brand_count) VALUES %s", s_rows)

            # 4. Apply Verified Counts
            print("Applying verified counts...")
            for cid, val in VERIFIED_TOP_CATEGORY_COUNTS.items():
                cur.execute("UPDATE categories SET sale_product_qty = %s WHERE category_id = %s OR algatop_id = %s", (val, cid, cid))

            conn.commit()
            print(f"\n[DONE] Success! Seeded {len(m_rows)} categories. Homepage stats should be restored.")

if __name__ == "__main__":
    seed_db()
