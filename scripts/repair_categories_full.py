import json
import psycopg2
from psycopg2.extras import execute_values

DB_URL = "postgresql://postgres:prosourcing123@localhost:5432/prosourcing"

def flatten_tree(nodes, parent_id=None, level=1):
    flattened = []
    for node in nodes:
        flattened.append({
            "id": node["id"],
            "name": node["name"],
            "parent_id": parent_id,
            "level": level,
            "is_leaf": len(node.get("children", [])) == 0
        })
        if node.get("children"):
            flattened.extend(flatten_tree(node["children"], node["id"], level + 1))
    return flattened

def run():
    # 1. 加载全量树数据 (4568 项)
    print("Loading full tree from file...")
    with open("d:/item/ProSourcing/tmp/root-artifacts/全部分类信息.txt", "r", encoding="utf-8") as f:
        tree_data = json.load(f)
    flat_tree = flatten_tree(tree_data)
    print(f"Loaded {len(flat_tree)} categories from master file.")

    # 2. 加载中文化缓存
    print("Loading CN cache...")
    try:
        with open("d:/item/ProSourcing/scripts/category_name_cn_cache.json", "r", encoding="utf-8") as f:
            cn_cache = json.load(f)
    except:
        cn_cache = {}
    print(f"Loaded {len(cn_cache)} translations from cache.")

    # 3. 连接数据库
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # 4. 执行修复与同步
    # 哥，咱们采取“精准手术”方案：
    # 对于每一个在 master 文件里的项，如果数据库里有（名字对上或者 ID 对上），就更新它的数字 ID 和中文名。
    # 如果数据库里没有，我们就考虑是否新增。
    
    print("Starting database sync...")
    
    # 获取数据库里现有的类目映射 (以俄文名作为 Key)
    cur.execute("SELECT category_id, name_ru, algatop_id, name_cn FROM categories")
    db_rows = cur.fetchall()
    db_by_name = {row[1]: row for row in db_rows if row[1]}
    # db_by_id 现在不可靠，因为很多 ID 是英文名

    count_updated = 0
    count_inserted = 0

    for item in flat_tree:
        aid = item["id"]
        ru = item["name"]
        pid = item["parent_id"]
        level = item["level"]
        is_leaf = item["is_leaf"]
        
        # 寻找对应的中文名
        cn = cn_cache.get(ru)
        
        # 如果数据库完全没有对应的俄文名记录，则插入。
        # 如果有，则更新。
        
        existing_row = db_by_name.get(ru)
        display_name = f"{ru} ({cn})" if cn else ru
        
        if existing_row:
            # 更新已存在的行
            old_cid = existing_row[0]
            update_query = """
                UPDATE categories SET 
                    category_id = %s,
                    algatop_id = %s,
                    category_name = %s,
                    name_ru = %s,
                    name_cn = %s,
                    parent_category_id = %s,
                    level = %s,
                    is_leaf = %s,
                    is_top_level = %s,
                    updated_at = now()
                WHERE category_id = %s
            """
            cur.execute(update_query, (aid, aid, display_name, ru, cn, pid, level, is_leaf, level == 1, old_cid))
            count_updated += 1
        else:
            # 插入或更新新类目
            insert_query = """
                INSERT INTO categories (
                    category_id, category_name, parent_category_id, 
                    algatop_id, name_ru, name_cn, 
                    level, is_leaf, is_top_level
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (category_id) DO UPDATE SET
                    algatop_id = EXCLUDED.algatop_id,
                    category_name = EXCLUDED.category_name,
                    name_ru = EXCLUDED.name_ru,
                    name_cn = EXCLUDED.name_cn,
                    parent_category_id = EXCLUDED.parent_category_id,
                    level = EXCLUDED.level,
                    is_leaf = EXCLUDED.is_leaf,
                    is_top_level = EXCLUDED.is_top_level,
                    updated_at = now()
            """
            cur.execute(insert_query, (aid, display_name, pid, aid, ru, cn, level, is_leaf, level == 1))
            count_inserted += 1

    conn.commit()
    print(f"SUCCESS!")
    print(f" - Updated: {count_updated}")
    print(f" - Inserted: {count_inserted}")
    print(f" - Total in DB now: {count_updated + count_inserted}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    run()
