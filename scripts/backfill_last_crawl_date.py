import os
import psycopg2
from datetime import datetime

def normalize_code(val):
    raw = str(val or "").strip()
    if not raw: return ""
    return raw.zfill(5) if raw.isdigit() else raw

def backfill():
    print("[ProSourcing] Backfilling crawl dates from analysis_tasks...")
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:prosourcing123@db:5432/prosourcing")
    
    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            # 1. Fetch all completed tasks
            cur.execute("""
                SELECT category_id, updated_at, created_at 
                FROM analysis_tasks 
                WHERE status = 'completed' 
                ORDER BY updated_at DESC
            """)
            tasks = cur.fetchall()
            print(f"Found {len(tasks)} completed tasks.")

            date_map = {}
            for cid, updated, created in tasks:
                code = normalize_code(cid)
                dt = str(updated or created or "")[:10]
                if code and dt and code not in date_map:
                    date_map[code] = dt

            # 2. Upsert into cache table
            print(f"Updating cache for {len(date_map)} categories...")
            for code, dt in date_map.items():
                cur.execute("""
                    INSERT INTO category_last_crawl_dates (category_code, last_crawl_date, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (category_code) 
                    DO UPDATE SET last_crawl_date = EXCLUDED.last_crawl_date, updated_at = EXCLUDED.updated_at
                """, (code, dt, datetime.now().isoformat()))
            
            conn.commit()
            print("[DONE] Category dates are now synchronized.")

if __name__ == "__main__":
    backfill()
