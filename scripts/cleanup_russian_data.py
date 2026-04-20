#!/usr/bin/env python3
import psycopg2
import re

DB_URL = "postgresql://postgres:prosourcing123@localhost:5432/prosourcing"

def cleanup_non_zh_en():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        cur.execute("SELECT id, category FROM analysis_tasks WHERE created_at >= '2026-04-20'")
        rows = cur.fetchall()
        
        to_delete = []
        for r in rows:
            cat = r[1]
            if not cat: continue
            # 检查是否包含俄文或其他非中英文字符
            # 哥，咱们保守点，只要包含 [А-я] 就删
            if re.search(r'[А-я]', cat):
                to_delete.append(str(r[0]))
        
        if not to_delete:
            print("未发现俄文乱码任务。")
            return

        print(f"发现 {len(to_delete)} 个俄文任务，正在清理...")
        cur.execute("DELETE FROM analysis_tasks WHERE id::text = ANY(%s)", (to_delete,))
        
        conn.commit()
        print(f"成功清理 {cur.rowcount} 条任务。")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"清理失败: {e}")

if __name__ == "__main__":
    cleanup_non_zh_en()
