#!/usr/bin/env python3
import os
import sys
import psycopg2
from datetime import datetime

# 哥，这里直接用生产环境的连接字符串
DB_URL = "postgresql://postgres:prosourcing123@localhost:5432/prosourcing"

def sync():
    print(f"[{datetime.now()}] 启动分类数据同步程序...")
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # 1. 获取 Master 表中的全量数据
        print("正在从 algatop_categories_master 获取数据...")
        cur.execute("SELECT algatop_id, name_ru, name_cn, name_en, parent_id, level, is_leaf FROM algatop_categories_master")
        master_rows = cur.fetchall()
        print(f"找到 {len(master_rows)} 条 Master 记录。")
        
        # 2. 准备同步到 categories 表
        # 哥，先把 categories 表里所有现有的 is_top_level 设为 False，我们要重新打标
        cur.execute("UPDATE categories SET is_top_level = False")
        
        print("正在同步到 categories 表...")
        for row in master_rows:
            aid, ru, cn, en, pid, level, is_leaf = row
            
            is_top = (level == 1)
            display_name = f"{ru} ({cn})" if cn else ru
            
            # 使用 upsert 逻辑
            upsert_query = """
            INSERT INTO categories (
                category_id, category_name, parent_category_id, 
                algatop_id, name_ru, name_cn, name_en, 
                level, is_leaf, is_top_level
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (category_id) DO UPDATE SET
                category_name = EXCLUDED.category_name,
                parent_category_id = EXCLUDED.parent_category_id,
                algatop_id = EXCLUDED.algatop_id,
                name_ru = EXCLUDED.name_ru,
                name_cn = EXCLUDED.name_cn,
                name_en = EXCLUDED.name_en,
                level = EXCLUDED.level,
                is_leaf = EXCLUDED.is_leaf,
                is_top_level = EXCLUDED.is_top_level,
                updated_at = now()
            """
            # 哥，category_id 统一用 aid (数字)，父类 ID 也对应上
            cur.execute(upsert_query, (aid, display_name, pid, aid, ru, cn, en, level, is_leaf, is_top))
            
        conn.commit()
        
        # 3. 统计一下最终结果
        cur.execute("SELECT count(*) FROM categories WHERE is_top_level = True")
        top_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM categories")
        total_count = cur.fetchone()[0]
        
        print(f"\n✅ 同步完成！")
        print(f" - 当前一级分类数量: {top_count} (目标应该是 21)")
        print(f" - 总分类数量: {total_count}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ 同步失败: {e}")

if __name__ == "__main__":
    sync()
