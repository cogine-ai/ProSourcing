import os
import sys
import json
import glob
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from datetime import datetime
from dotenv import load_dotenv

# 哥，加载环境配置
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)
load_dotenv()

# 数据库连接配置 (默认生产环境连接字符串)
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:prosourcing123@db:5432/prosourcing")
if "@db:" in DB_URL and sys.platform == "win32":
    # 哥，如果是 Windows 环境本地运行，把 db 域名换成 127.0.0.1
    DB_URL = DB_URL.replace("@db:", "@127.0.0.1:")

def get_conn():
    return psycopg2.connect(DB_URL)

def print_header(title):
    print(f"\n{'='*50}\n[ {title} ]\n{'='*50}")

# ==========================================
# 模式 1: 批量导入本地 JSON
# ==========================================
def mode_import_json():
    print_header("模式 1: 批量导入本地 JSON 数据")
    pattern = os.path.join(PROJECT_ROOT, "output", "json", "rpa_output_*.json")
    files = glob.glob(pattern)
    print(f"找到 {len(files)} 个待查 JSON 文件...")

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    count = 0
    for fpath in files:
        fname = os.path.basename(fpath)
        # 尝试提取 UUID
        tid_raw = fname.replace("rpa_output_", "").replace(".json", "")
        try:
            tid = str(uuid.UUID(tid_raw))
        except:
            continue
        
        # 检查是否已入库
        cur.execute("SELECT id FROM analysis_tasks WHERE id = %s", (tid,))
        if cur.fetchone():
            continue
            
        print(f"正在导入新任务: {tid}...")
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            niche = data.get('niche_stats', {})
            # 插入任务
            cur.execute(
                "INSERT INTO analysis_tasks (id, category, category_id, status, category_stats, trend_data) VALUES (%s, %s, %s, %s, %s, %s)",
                (tid, niche.get('category_name'), niche.get('category_id'), 'completed', json.dumps(niche, ensure_ascii=False), json.dumps(data.get('trend', []), ensure_ascii=False))
            )
            count += 1
        except Exception as e:
            print(f"导入失败 {tid}: {e}")
            
    conn.commit()
    cur.close()
    conn.close()
    print(f"完成！共新导入 {count} 个任务数据。")

# ==========================================
# 模式 2: 重置故障任务
# ==========================================
def mode_reset_tasks():
    print_header("模式 2: 重置故障/卡死任务")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE analysis_tasks SET status='pending', progress=0, error_msg=NULL WHERE status IN ('failed', 'stuck')")
    affected = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"成功重置 {affected} 个任务至 'pending' 状态。")

# ==========================================
# 模式 3: 补全大类分类信息
# ==========================================
def mode_backfill_categories():
    print_header("模式 3: 补全任务表大类名称")
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 构建映射表
    cur.execute("SELECT algatop_id, name_cn, parent_id, level FROM algatop_categories_master")
    all_cats = {str(row['algatop_id']): row for row in cur.fetchall()}
    
    def find_top(cid):
        cid_str = str(cid)
        curr = all_cats.get(cid_str)
        for _ in range(5):
            if not curr or not curr['parent_id'] or curr['level'] <= 1:
                return curr['name_cn'] if curr else None
            curr = all_cats.get(str(curr['parent_id']))
        return curr['name_cn'] if curr else None

    cur.execute("SELECT id, category_id FROM analysis_tasks WHERE top_category_name_cn IS NULL")
    tasks = cur.fetchall()
    print(f"发现 {len(tasks)} 条待补全任务...")
    
    updated = 0
    for t in tasks:
        top_name = find_top(t['category_id'])
        if top_name:
            cur.execute("UPDATE analysis_tasks SET top_category_name_cn = %s WHERE id = %s", (top_name, t['id']))
            updated += 1
            
    conn.commit()
    cur.close()
    conn.close()
    print(f"完成！成功回填 {updated} 条大类信息。")

# ==========================================
# 模式 4: 重算统计指标 (CR3 / 有效数)
# ==========================================
def mode_recalc_stats():
    print_header("模式 4: 重算统计指标 (CR3 / 有效数)")
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, category FROM analysis_tasks WHERE status = 'completed'")
    tasks = cur.fetchall()
    
    updated = 0
    now = datetime.now()
    
    def force_num(v):
        if v is None: return 0.0
        try: return float(str(v).replace(' ', '').replace(',', ''))
        except: return 0.0

    for t in tasks:
        tid = t['id']
        fpath = os.path.join(PROJECT_ROOT, "output", "json", f"rpa_output_{tid}.json")
        if not os.path.exists(fpath): continue
        
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            niche = data.get('niche_stats', {})
            prods = data.get('products', [])
            
            # 1. 算 Top3 和 CR3
            amounts = sorted([force_num(p.get('sale_amount', 0)) for p in prods], reverse=True)
            top3_sum = sum(amounts[:3])
            total_sum = force_num(niche.get('sale_amount', 0))
            cr3 = f"{(top3_sum / total_sum * 100):.1f}%" if total_sum > 0 else "0.0%"
            
            # 2. 算有效数 (销量>=60, 评论>=15)
            valid_count = 0
            for p in prods:
                if force_num(p.get('sale_qty',0)) >= 60 and force_num(p.get('review_qty',0)) >= 15:
                    valid_count += 1
            
            niche['top3_revenue'] = top3_sum
            niche['cr3'] = cr3
            niche['valid_product_count'] = valid_count
            
            cur.execute("UPDATE analysis_tasks SET category_stats = %s WHERE id = %s", (json.dumps(niche, ensure_ascii=False), tid))
            updated += 1
        except Exception as e:
            print(f"处理任务 {tid} 失败: {e}")
        
    conn.commit()
    cur.close()
    conn.close()
    print(f"完成！成功校准 {updated} 个任务的统计指标。")

# ==========================================
# 模式 5: 同步抓取日期到分类表
# ==========================================
def mode_sync_dates():
    print_header("模式 5: 同步最新抓取日期至分类表")
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 查每个类目最新的任务日期
    cur.execute("""
        SELECT category_id, MAX(updated_at) as last_date 
        FROM analysis_tasks 
        WHERE status = 'completed' 
        GROUP BY category_id
    """)
    dates = cur.fetchall()
    
    updated = 0
    for d in dates:
        cur.execute(
            "UPDATE algatop_categories_master SET last_crawl_date = %s WHERE algatop_id = %s",
            (d['last_date'], d['category_id'])
        )
        updated += cur.rowcount
        
    conn.commit()
    cur.close()
    conn.close()
    print(f"完成！已更新 {updated} 条分类的最新采集时间。")

def main():
    while True:
        print("\n" + "*"*40)
        print("   ProSourcing 万能运维工具箱   ")
        print("*"*40)
        print("1. 批量导入本地 JSON 数据 (JSON -> DB)")
        print("2. 重置故障/卡死任务 (Reset Status)")
        print("3. 补全任务表大类名称 (Backfill Top Category)")
        print("4. 重算统计指标 (Recalc CR3 & Valid Count)")
        print("5. 同步最新抓取日期至分类表 (Sync Crawl Date)")
        print("0. 退出")
        
        choice = input("\n请选择功能 (0-5): ")
        
        if choice == '1': mode_import_json()
        elif choice == '2': mode_reset_tasks()
        elif choice == '3': mode_backfill_categories()
        elif choice == '4': mode_recalc_stats()
        elif choice == '5': mode_sync_dates()
        elif choice == '0': break
        else: print("无效选择，请重新输入。")

if __name__ == "__main__":
    main()
