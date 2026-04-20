#!/usr/bin/env python3
import os
import sys
import psycopg2
from datetime import datetime

# 加载项目环境
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# 哥，这里直接用生产环境的连接字符串
DB_URL = "postgresql://postgres:prosourcing123@localhost:5432/prosourcing"

def cleanup():
    print(f"[{datetime.now()}] 启动数据库清理程序...")
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # 1. 先查一下有多少待删记录
        # 哥，逻辑是：今天创建的，且 category 包含俄文字符的，或者是那些明显是误导的英文名称
        query_check = """
        SELECT id, category, created_at FROM analysis_tasks 
        WHERE created_at >= '2026-04-20'
        AND (
            category ~ '[А-я]' 
            OR category IN ('Shoes', 'Women shoes', 'Men shoes', 'Kids shoes')
        )
        """
        cur.execute(query_check)
        rows = cur.fetchall()
        
        if not rows:
            print("未发现符合条件的误导入任务，无需清理。")
            return

        print(f"发现 {len(rows)} 个可疑任务：")
        for r in rows:
            print(f" - ID: {r[0]}, Category: {r[1]}, Created: {r[2]}")
            
        # 2. 执行物理删除
        # 哥，由于有 ON DELETE CASCADE，关联的 products_raw_data 和 products_calculated_metrics 会自动消失
        delete_ids = [str(r[0]) for r in rows]
        query_delete = "DELETE FROM analysis_tasks WHERE id::text = ANY(%s)"
        cur.execute(query_delete, (delete_ids,))
        
        conn.commit()
        print(f"\n[OK] 成功清理 {cur.rowcount} 条任务及其关联的所有抓取数据！")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] 清理失败: {e}")

if __name__ == "__main__":
    cleanup()
