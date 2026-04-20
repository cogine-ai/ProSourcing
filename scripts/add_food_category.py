#!/usr/bin/env python3
import psycopg2

DB_URL = "postgresql://postgres:prosourcing123@localhost:5432/prosourcing"

def add_food():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # 补全食物大类
        query = """
        INSERT INTO categories (
            category_id, category_name, parent_category_id, 
            algatop_id, name_ru, name_cn, 
            level, is_leaf, is_top_level, is_has_subcategory
        ) VALUES (
            '01793', '食物 (Продукты питания)', NULL, 
            '01793', 'Продукты питания', '食物', 
            1, True, True, 0
        ) ON CONFLICT (category_id) DO UPDATE SET 
            is_top_level = True,
            category_name = EXCLUDED.category_name
        """
        cur.execute(query)
        conn.commit()
        print("✅ 成功补全'食物'大类！")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ 补全失败: {e}")

if __name__ == "__main__":
    add_food()
