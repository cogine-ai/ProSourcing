import psycopg2

def sync():
    conn = psycopg2.connect('postgresql://postgres:prosourcing123@localhost:5432/prosourcing')
    cur = conn.cursor()
    
    # 1. 从 categories 获取完美数据
    # 注意：categories 表里的 parent_category_id 对应 master 的 parent_id
    cur.execute("""
        SELECT algatop_id, name_ru, name_cn, parent_category_id, level, is_leaf 
        FROM categories
    """)
    rows = cur.fetchall()
    print(f"Read {len(rows)} categories from categories table.")
    
    # 2. 写入 algatop_categories_master
    upsert_sql = """
        INSERT INTO algatop_categories_master (algatop_id, name_ru, name_cn, parent_id, level, is_leaf, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (algatop_id) DO UPDATE SET
            name_ru = EXCLUDED.name_ru,
            name_cn = EXCLUDED.name_cn,
            parent_id = EXCLUDED.parent_id,
            level = EXCLUDED.level,
            is_leaf = EXCLUDED.is_leaf,
            updated_at = NOW()
    """
    
    count = 0
    for row in rows:
        cur.execute(upsert_sql, row)
        count += 1
    
    conn.commit()
    print(f"Successfully synced {count} categories to algatop_categories_master.")
    conn.close()

if __name__ == "__main__":
    sync()
