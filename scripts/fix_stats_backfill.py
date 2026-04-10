import os
import sys
import json
import glob
from datetime import datetime

# 哥，加载项目环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from core.final_pipeline import supabase as sb
    from core.final_pipeline import ENV_MOD
except:
    print("[ERROR] 环境加载失败，请确认执行路径。")
    sys.exit(1)

def backfill_stats():
    print(f"====================================================")
    print(f"[FINAL-RECOVER] 最终精准回填逻辑启动")
    
    import re
    def force_num(v):
        if v is None: return 0
        if isinstance(v, (int, float)): return v
        s = str(v).replace(' ', '').replace(',', '').replace('.', '')
        nums = re.findall(r"\d+", s)
        return int(nums[0]) if nums else 0

    # 1. 获取所有任务
    res = sb.table("analysis_tasks").select("id, category_id, category, category_stats").eq("status", "completed").execute()
    tasks = res.data
    
    count = 0
    now = datetime.now()
    for t in tasks:
        tid = t.get('id')
        cat_name = t.get('category', '未知')
        
        # --- A. 路径定位 ---
        target_file = None
        fast_path = f"/app/output/json/rpa_output_{tid}.json"
        if os.path.exists(fast_path):
            target_file = fast_path
        else:
            matches = glob.glob(f"**/rpa_output_{tid}.json", recursive=True)
            if matches: target_file = matches[0]
        
        if not target_file:
            print(f"\n[SKIP] {cat_name} ({tid}) - 未找到 JSON 文件")
            continue

        print(f"\n--- [Task ID: {tid}] {cat_name} ---")
        
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                raw_json = json.load(f)
        except Exception as e:
            print(f"  [ERROR] 读取失败: {e}")
            continue

        # --- B. 提取大盘 niche_stats ---
        n = raw_json.get('niche_stats', {})
        products_list = raw_json.get('products', [])
        
        final_stats = {}
        # 1. 销量/商品数/总金额
        final_stats['sale_product_qty'] = force_num(n.get('sale_product_qty'))
        final_stats['sale_qty'] = force_num(n.get('sale_qty'))
        total_amount = float(force_num(n.get('sale_amount')))
        final_stats['sale_amount'] = total_amount
        final_stats['sale_merchant_qty'] = force_num(n.get('sale_seller_qty') or n.get('merchant_qty'))

        # 2. 哥，关键动作：从商品列表里算出“前三营收”
        # 先按销售额倒序排列
        for p in products_list:
            p['_amount_val'] = force_num(p.get('sale_amount'))
        
        sorted_prods = sorted(products_list, key=lambda x: x.get('_amount_val', 0), reverse=True)
        top3_sum = sum(p.get('_amount_val', 0) for p in sorted_prods[:3])
        
        final_stats['top3_revenue'] = float(top3_sum)
        
        # 3. 计算 CR3
        if total_amount > 0:
            final_stats['cr3'] = f"{(top3_sum / total_amount * 100):.1f}%"
        else:
            final_stats['cr3'] = "0.0%"

        # --- C. 计算精选数 (有效数) ---
        # 就在内存里直接拿 JSON 的 products 来算，不用再去查 DB，保证绝对对应
        valid_count = 0
        for p in products_list:
            s_qty = force_num(p.get('sale_qty'))
            r_qty = force_num(p.get('review_qty'))
            p_val = force_num(p.get('sale_price'))
            
            days = 999
            if p.get('created_dt'):
                try:
                    dt_str = p['created_dt'].replace(' ', 'T').split('.')[0]
                    if 'T' not in dt_str: dt_str = dt_str.replace(' ', 'T')
                    dt = datetime.fromisoformat(dt_str)
                    days = (now - dt).days
                except: pass
            
            if s_qty >= 60 and r_qty >= 15 and p_val >= 800 and days <= 300:
                valid_count += 1
        
        final_stats['valid_product_count'] = valid_count
        final_stats['valid_product_qty'] = valid_count

        # --- D. 回写 ---
        try:
            update_data = json.dumps(final_stats, ensure_ascii=False) if ENV_MOD == "production" else final_stats
            sb.table("analysis_tasks").update({"category_stats": update_data}).eq("id", tid).execute()
            print(f"  [SUCCESS] 总数: {final_stats['sale_product_qty']}, 有效数: {valid_count}, 前三营收: {top3_sum}, CR3: {final_stats['cr3']}")
        except Exception as e:
            print(f"  [DB-ERROR] 写入失败: {e}")

        count += 1

    print(f"\n[FINISH] 彻底搞定！共校准 {count} 个类目指标。")

if __name__ == "__main__":
    backfill_stats()
