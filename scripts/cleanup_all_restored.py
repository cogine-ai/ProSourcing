#!/usr/bin/env python3
import psycopg2

DB_URL = "postgresql://postgres:prosourcing123@localhost:5432/prosourcing"

def cleanup_all_restored():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # 查找所有包含 _rpa_output_ 的任务
        query = "SELECT id, category FROM analysis_tasks WHERE category LIKE '%_rpa_output_%'"
        cur.execute(query)
        rows = cur.fetchall()
        
        if not rows:
            print("未发现更多恢复的任务。")
            return

        print(f"发现 {len(rows)} 个恢复的任务，正在清理...")
        delete_ids = [str(r[0]) for r in rows]
        cur.execute("DELETE FROM analysis_tasks WHERE id::text = ANY(%s)", (delete_ids,))
        
        conn.commit()
        print(f"成功清理 {cur.rowcount} 条任务。")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"清理失败: {e}")

if __name__ == "__main__":
    cleanup_all_restored()
