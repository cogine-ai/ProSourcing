import json
import os
import psycopg2
from psycopg2.extras import execute_values

def find_data_file():
    candidates = [
        "/app/scripts/full_category_data.json",
        "scripts/full_category_data.json",
        "/app/scripts/新建文件夹/full_category_data.json",
        "full_category_data.json"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def extract_list(data):
    # 智能解析：找到真正的列表
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # 可能是索引字典 {"0": {...}, "1": {...}}
        if all(k.isdigit() for k in list(data.keys())[:10]):
            return list(data.values())
        # 可能是包装字典 {"items": [...], "status": "ok"}
        for k, v in data.items():
            if isinstance(v, list) and len(v) > 10:
                print(f"🎯 Auto-detected data in key: '{k}'")
                return v
    return None

def seed_db():
    print("🚀 [ProSourcing] Starting SMART JSON seed process...")
    json_path = find_data_file()
    if not json_path:
        print("❌ Error: File not found.")
        return

    print(f"📖 Reading JSON: {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # 哥，针对新版 JSON 结构 {"master": [], "stats": []} 进行适配
    master_list = []
    stats_list = []
    
    if isinstance(raw_data, dict):
        master_list = raw_data.get('master', [])
        stats_list = raw_data.get('stats', [])
        # 如果 master 为空，尝试用旧的自动探测逻辑
        if not master_list:
            master_list = extract_list(raw_data) or []
    elif isinstance(raw_data, list):
        master_list = raw_data
        
    if not master_list:
        print("❌ Error: Could not extract master list from JSON.")
        return

    print(f"📊 Items to process: Master={len(master_list)}, Stats={len(stats_list)}")

    try:
        db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:prosourcing123@db:5432/prosourcing")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # 1. Categories Master
        if master_list:
            print("🛠️ Updating master...")
            master_data = []
            for item in master_list:
                if not isinstance(item, dict): continue
                master_data.append((
                    item.get('algatop_id'),
                    item.get('name_ru'),
                    item.get('name_cn'),
                    item.get('name_en'),
                    item.get('parent_id'),
                    item.get('level'),
                    item.get('is_leaf', False),
                    item.get('monthly_sales', 0)
                ))
            
            cur.execute("TRUNCATE TABLE algatop_categories_master CASCADE;")
            execute_values(cur, "INSERT INTO algatop_categories_master (algatop_id, name_ru, name_cn, name_en, parent_id, level, is_leaf, monthly_sales) VALUES %s", master_data)
            print(f"✅ Master injected: {len(master_data)} items.")

        # 2. Roots Stats (如果 JSON 里有 stats 节点则优先使用，否则尝试从 master 里捞)
        final_stats_list = stats_list
        if not final_stats_list:
            print("⚠️ Stats list empty, falling back to master for level 1 stats...")
            final_stats_list = [item for item in master_list if isinstance(item, dict) and (item.get('is_top_level') or item.get('level') == 1)]

        if final_stats_list:
            print(f"🔥 Updating {len(final_stats_list)} root stats...")
            stats_data = []
            for item in final_stats_list:
                if not isinstance(item, dict): continue
                stats_data.append((
                    item.get('algatop_id', item.get('id')),
                    item.get('sales_qty', 0),
                    item.get('revenue', 0),
                    item.get('product_count', 0),
                    item.get('seller_count', 0),
                    item.get('brand_count', 0)
                ))
            
            cur.execute("TRUNCATE TABLE algatop_top_category_stats CASCADE;")
            execute_values(cur, "INSERT INTO algatop_top_category_stats (algatop_id, sales_qty, revenue, product_count, seller_count, brand_count) VALUES %s", stats_data)
            print(f"✅ Stats injected: {len(stats_data)} items.")

        conn.commit()
    except Exception as e:
        print(f"❌ DB Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    seed_db()
