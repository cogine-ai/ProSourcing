import os
import psycopg2
from datetime import datetime

def recover():
    print("[ProSourcing] Starting Category ID recovery from History...")
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:prosourcing123@db:5432/prosourcing")
    
    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            # 1. 查找所有没有 ID 的已完成任务
            cur.execute("""
                SELECT id, category, updated_at 
                FROM analysis_tasks 
                WHERE (category_id IS NULL OR category_id = '') 
                  AND status = 'completed'
            """)
            tasks = cur.fetchall()
            print(f"Total historical tasks to repair: {len(tasks)}")

            success_count = 0
            for tid, full_name, dt in tasks:
                # 提取俄文名：去掉 _rpa_output_ 及其后缀
                pure_name = str(full_name).split('_rpa_output_')[0].strip()
                
                # 在新版 categories 表里按名字反查数字 ID
                cur.execute("""
                    SELECT algatop_id FROM categories 
                    WHERE name_ru = %s OR category_name = %s 
                    LIMIT 1
                """, (pure_name, pure_name))
                
                row = cur.fetchone()
                if row:
                    target_id = row[0]
                    # 补回任务表的 ID
                    cur.execute("UPDATE analysis_tasks SET category_id = %s WHERE id = %s", (target_id, tid))
                    # 更新分类树的日期缓存
                    cur.execute("""
                        INSERT INTO category_last_crawl_dates (category_code, last_crawl_date, updated_at)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (category_code) 
                        DO UPDATE SET last_crawl_date = EXCLUDED.last_crawl_date, updated_at = EXCLUDED.updated_at
                    """, (target_id, str(dt)[:10], datetime.now().isoformat()))
                    
                    success_count += 1
                    if success_count % 10 == 0:
                        print(f"  [Progress] Repaired {success_count} tasks...")

            conn.commit()
            print(f"\n[DONE] Successfully repaired {success_count} tasks.")
            print("Now refresh your 'Tasks' page, the dates should be back!")

if __name__ == "__main__":
    recover()
