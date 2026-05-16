import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:prosourcing123@127.0.0.1:5432/prosourcing")
if "@db:" in DB_URL:
    DB_URL = DB_URL.replace("@db:", "@127.0.0.1:")

def build_category_map(cursor):
    """构建 品类ID -> 大类中文名 的映射"""
    print("正在构建全量分类层级地图...")
    cursor.execute("SELECT algatop_id, name_cn, name_ru, parent_id, level FROM algatop_categories_master")
    all_cats = {row['algatop_id']: row for row in cursor.fetchall()}
    
    # 缓存：品类ID -> 大类中文名
    id_to_top_name = {}
    
    for cid, row in all_cats.items():
        curr = row
        # 向上爬 5 层（保险起见）直到找到顶级分类
        for _ in range(5):
            if not curr.get('parent_id') or curr['level'] <= 1:
                break
            parent_id = curr['parent_id']
            if parent_id in all_cats:
                curr = all_cats[parent_id]
            else:
                break
        id_to_top_name[cid] = curr['name_cn']
        
    return id_to_top_name, all_cats

def backfill():
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    id_to_top_name, all_cats_data = build_category_map(cursor)
    
    # 构建：品类中文名/俄文名 -> 大类中文名 的备选地图
    name_to_top_name = {}
    for cid, row in all_cats_data.items():
        top_name = id_to_top_name.get(cid)
        if top_name:
            if row['name_cn']: name_to_top_name[row['name_cn']] = top_name
            if row['name_ru']: name_to_top_name[row['name_ru']] = top_name

    print("地图构建完成。正在开始回填任务表...")
    
    # 查找需要回填的任务（包括 top_category_name_cn 为空、None 字符串或包含乱码的情况）
    cursor.execute("SELECT id, category, category_id FROM analysis_tasks")
    tasks = cursor.fetchall()
    
    update_count = 0
    for t in tasks:
        task_id = t['id']
        cat_name = t['category']
        cat_id = t['category_id']
        
        # 尝试通过 ID 匹配
        top_name = id_to_top_name.get(cat_id)
        
        # 如果 ID 没匹配上，通过名称匹配
        if not top_name:
            top_name = name_to_top_name.get(cat_name)
            
        if top_name:
            cursor.execute(
                "UPDATE analysis_tasks SET top_category_name_cn = %s WHERE id = %s",
                (top_name, task_id)
            )
            update_count += 1
            if update_count % 50 == 0:
                print(f"已回填 {update_count} 条...")

    conn.commit()
    print(f"\n--- 处理完成 ---")
    print(f"共扫描 {len(tasks)} 条任务，成功修复/回填 {update_count} 条数据。")
    conn.close()

if __name__ == "__main__":
    backfill()
