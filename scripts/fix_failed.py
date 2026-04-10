import os
import sys
import subprocess
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:prosourcing123@db:5432/prosourcing")

def get_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception:
        if "db:5432" in DATABASE_URL:
            alt_url = DATABASE_URL.replace("db:5432", "127.0.0.1:5432")
            print(f"[DB] 正在尝试连接: {alt_url} ...")
            return psycopg2.connect(alt_url)
        raise

def restart():
    print("="*60)
    print(" ProSourcing 现场失败任务一键修复 (v1.2)")
    print("="*60)
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 找失败的任务
        cursor.execute("SELECT id, category, category_id FROM analysis_tasks WHERE status IN ('failed', 'error', 'cancelled')")
        tasks = cursor.fetchall()
        
        if not tasks:
            print("\n[INFO] 未发现失败任务。")
            return
            
        print(f"\n[SCAN] 共有 {len(tasks)} 个任务需要重跑。")
        confirm = input("\n哥，是否确认开始? (y/n): ")
        if confirm.lower() != 'y': return

        # 循环依次重跑
        for i, t in enumerate(tasks, 1):
            tid, cid, name = t['id'], t['category_id'], t['category']
            print(f"\n[{i}/{len(tasks)}] 正在重跑: {name} (ID: {tid})")
            
            # 1. 数据库状态重置
            cursor.execute("UPDATE analysis_tasks SET status='pending', progress=0, error_msg=NULL WHERE id=%s", (tid,))
            conn.commit()
            
            # 2. 跑脚本
            try:
                # 调 RPA 爬虫
                print("  -> 步骤 1/2: 正在执行爬虫...")
                subprocess.check_call([sys.executable, "core/algatop_rpa_scraper.py", str(cid), str(tid)])
                
                # 调报告生成
                print("  -> 步骤 2/2: 正在生成分析报告...")
                out_path = os.path.abspath(f"output/rpa_output_{tid}.json")
                subprocess.check_call([sys.executable, "core/rpa_final_pipeline.py", str(tid), out_path])
                
                print("  [SUCCESS] 该任务修复完成。")
            except Exception as e:
                print(f"  [ERROR] 修复失败: {e}")
                
            time.sleep(1)
            
    except Exception as e:
        print(f"\n[FATAL] 脚本异常: {e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    restart()
