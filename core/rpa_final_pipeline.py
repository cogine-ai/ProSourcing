import json
import os
import requests
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenPyxlImage
import sys

# 设置项目根目录
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.scoring import ScoringEngine

# ==========================================
# 核心配置
# ==========================================
INPUT_FILE = "d:/item/ProSourcing/output/rpa_output.json"
TEMPLATE_PATH = "d:/item/ProSourcing/AI产品开发.xlsx"
OUTPUT_DIR = "d:/item/ProSourcing/output"
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
os.makedirs(IMAGE_DIR, exist_ok=True)

def download_image(url, sku):
    """由于是真实浏览器预览链接，这里需要支持从 CDN 下载"""
    if not url: return None
    path = os.path.join(IMAGE_DIR, f"{sku}.jpg")
    if os.path.exists(path): return path
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(path, 'wb') as f: f.write(r.content)
            return path
    except: pass
    return None

# ==========================================
# 核心处理逻辑 (含 V2.0 数据库同步)
# ==========================================
from supabase import create_client, Client
SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def process_rpa_data(task_id=None):
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 找不到输入文件: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        rpa_data = json.load(f)

    niche_stats = rpa_data.get("niche_stats", {})
    products = rpa_data.get("products", [])
    trend = rpa_data.get("trend", [])

    if not products:
        print("❌ 商品列表为空，请检查采集环节。")
        return

    # 1. 更新任务大盘数据 (analysis_tasks)
    if task_id and niche_stats:
        print(f"📡 正在同步类目大盘与趋势数据 (Task: {task_id})...")
        update_task = {
            "category_id": niche_stats.get("category_ext_id"),
            "category_stats": niche_stats,
            "trend_data": trend,
            "up_categories": niche_stats.get("up_categories_json")
        }
        supabase.table("analysis_tasks").update(update_task).eq("id", task_id).execute()

    # 2. 处理商品数据并同步 (products_raw_data & products_calculated_metrics)
    processed_results = []
    raw_payloads = []
    calc_payloads = []

    cat_name = niche_stats.get("category_name", "未知品类")
    cat_sales = niche_stats.get("sale_qty", 0)
    cat_product_count = niche_stats.get("sale_product_qty", 1)
    cat_ratio = cat_sales / cat_product_count if cat_product_count > 0 else 0
    cat_path = " > ".join([c["category_name"] for c in niche_stats.get("up_categories_json", [])])

    print(f"🔥 正在同步 {len(products)} 条商品详情至 V2.0 数据库...")

    for p in products:
        sku = str(p.get('product_code'))
        m_sales = int(p.get('sale_qty', 0))
        m_amount = float(p.get('sale_amount', 0))
        reviews = int(p.get('review_qty', 0))
        price = float(p.get('sale_price', 0))
        
        # 计算评分
        s_sales = ScoringEngine.score_monthly_sales(m_sales)
        s_reviews = ScoringEngine.score_reviews(reviews)
        s_price = ScoringEngine.score_price(price)
        
        created_dt_str = p.get('created_dt')
        days_since_creation = 0
        if created_dt_str:
            try:
                dt = datetime.strptime(created_dt_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                days_since_creation = (datetime.now() - dt).days
            except: pass
        
        s_days_per_review = ScoringEngine.score_days_per_review(days_since_creation, reviews)
        total_score = s_sales + s_reviews + s_price + s_days_per_review

        # 构造 Raw Payload (对齐 V2.0 Schema)
        raw_payloads.append({
            "sku": sku,
            "task_id": task_id,
            "product_name": p.get('product_name'),
            "brand_name": p.get('brand_name'),
            "gen_brand_id": p.get('gen_brand_id'),
            "product_url": p.get('product_url'),
            "sale_price": price,
            "product_rate": float(p.get('product_rate') or 0),
            "review_qty": reviews,
            "merchant_count": int(p.get('merchant_count') or 0),
            "sale_qty": m_sales,
            "sale_amount": m_amount,
            "amount_abc": p.get('amount_abc'),
            "amount_prc": float(p.get('amount_prc') or 0),
            "preview_image_list": p.get('preview_image_list'),
            "created_dt": created_dt_str,
            "category_name": p.get('category_name'),
            "category_ext_id": p.get('category_ext_id'),
            "restrict_type": p.get('restrict_type')
        })

        # 构造 Calc Payload
        calc_payloads.append({
            "sku": sku,
            "task_id": task_id,
            "total_score": total_score
        })

        # 导出用数据
        img_url = ""
        try:
            imgs = p.get('preview_image_list')
            if isinstance(imgs, str): imgs = json.loads(imgs)
            if imgs: img_url = imgs[0].get('large')
        except: pass

        processed_results.append({
            "sku": sku, "name": p.get('product_name'), "url": p.get('product_url'),
            "image_url": img_url, "brand": p.get('brand_name'),
            "monthly_sales": m_sales, "reviews": reviews, "price": price,
            "days_since_creation": days_since_creation,
            "created_dt": created_dt_str.split(' ')[0] if created_dt_str else "N/A",
            "total_score": total_score, "cat_path": cat_path
        })

    # 批量同步至 Supabase
    if raw_payloads:
        supabase.table("products_raw_data").upsert(raw_payloads).execute()
        supabase.table("products_calculated_metrics").upsert(calc_payloads).execute()
        print(f"✅ 数据库同步完成: 35 个字段已入库。")

    # 3. 产生 Excel 报告
    processed_results.sort(key=lambda x: x['total_score'], reverse=True)
    output_filename = f"Report_{cat_name}_{datetime.now().strftime('%m%d_%H%M')}.xlsx"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    try:
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active
        headers = ['日期', '品类', '图', '月销', '评论', '售价', '单品均销', '上架', '天数', '评分', '链接']
        for col, h in enumerate(headers, 1): ws.cell(row=1, column=col, value=h)
        for i, p in enumerate(processed_results, start=2):
            ws.row_dimensions[i].height = 60
            ws.cell(row=i, column=1, value=datetime.now().strftime("%Y-%m-%d"))
            ws.cell(row=i, column=2, value=p['cat_path'])
            img_path = download_image(p['image_url'], p['sku'])
            if img_path:
                try:
                    img = OpenPyxlImage(img_path); img.width, img.height = 70, 70
                    ws.add_image(img, f"C{i}")
                except: ws.cell(row=i, column=3, value="Err")
            ws.cell(row=i, column=4, value=p['monthly_sales'])
            ws.cell(row=i, column=5, value=p['reviews'])
            ws.cell(row=i, column=6, value=p['price'])
            ws.cell(row=i, column=7, value=f"{cat_ratio:.1f}")
            ws.cell(row=i, column=8, value=p['created_dt'])
            ws.cell(row=i, column=9, value=p['days_since_creation'])
            ws.cell(row=i, column=10, value=p['total_score'])
            ws.cell(row=i, column=11, value=p['url'])
        wb.save(output_path)
        print(f"✅ Excel 已生成: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Excel 导出失败: {e}")

if __name__ == "__main__":
    tid = sys.argv[1] if len(sys.argv) > 1 else None
    process_rpa_data(tid)
