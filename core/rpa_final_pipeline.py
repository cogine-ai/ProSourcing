import json
import os
import requests
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenPyxlImage
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置项目根目录
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.scoring import ScoringEngine

# ==========================================
# 核心配置
# ==========================================
INPUT_FILE = "d:/item/ProSourcing/output/rpa_output.json"
TEMPLATE_PATH = "d:/item/ProSourcing/AI产品开发.xlsx"
OUTPUT_DIR = "d:/item/ProSourcing/output"
# 优先从环境变量读取，避免图片入包导致项目臃肿
IMAGE_DIR = os.getenv("IMAGE_STORAGE_PATH", os.path.join(OUTPUT_DIR, "images"))
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

import uuid

def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except:
        return False

def process_rpa_data(task_id=None, input_file=None):
    # 如果没传 input_file，则尝试拼接默认路径
    target_file = input_file or os.path.join(OUTPUT_DIR, f"rpa_output_{task_id}.json")
    
    if not os.path.exists(target_file):
        print(f"[ERROR] 找不到输入文件: {target_file}")
        sys.exit(1)

    with open(target_file, "r", encoding="utf-8") as f:
        rpa_data = json.load(f)

    niche_stats = rpa_data.get("niche_stats", {})
    products = rpa_data.get("products", [])[:160]  # 哥，本次多页采集同步 160 条 (8页)
    trend = rpa_data.get("trend", [])

    if not products:
        print("[ERROR] 商品列表为空，请检查采集环节。")
        return

    # 翻译商品名称
    from deep_translator import GoogleTranslator
    import concurrent.futures

    def translate_name(p):
        raw_name = p.get('product_name')
        if not raw_name: return p
        try:
            translator = GoogleTranslator(source='auto', target='zh-CN')
            p['product_name'] = translator.translate(raw_name)
        except:
            pass
        return p

    print(f"[SYNC] 正在翻译 {len(products)} 条商品名称...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        products = list(executor.map(translate_name, products))

    # 校验 Task ID，如果无效则创建新任务
    final_task_id = task_id
    if not is_valid_uuid(task_id):
        print(f"[INFO] Task ID '{task_id}' 无效，正在数据库中创建新任务...")
        new_task = {
            "category": f"RPA采集_{niche_stats.get('category_name', '未知')}_{datetime.now().strftime('%m%d_%H%M')}",
            "status": "completed",
            "category_id": niche_stats.get("category_ext_id"),
            "category_stats": niche_stats,
            "trend_data": trend
        }
        res = supabase.table("analysis_tasks").insert(new_task).execute()
        if res.data:
            final_task_id = res.data[0]["id"]
            print(f"[SUCCESS] 已创建新任务: {final_task_id}")
    else:
        # 即使 Task ID 有效，也尝试更新大盘数据
        if niche_stats:
            print(f"[SYNC] 正在同步类目大盘与趋势数据 (Task: {final_task_id})...")
            update_task = {
                "category_id": niche_stats.get("category_ext_id"),
                "category_stats": niche_stats,
                "trend_data": trend,
                "up_categories": niche_stats.get("up_categories_json"),
                "status": "completed",
                "finished_at": datetime.now().isoformat()
            }
            # 临时处理：数据库表中目前没有 finished_at 字段，先移除以防止报错
            update_task.pop("finished_at", None)
            
            supabase.table("analysis_tasks").update(update_task).eq("id", final_task_id).execute()

    # 2. 处理商品数据并同步 (products_raw_data & products_calculated_metrics)
    processed_results = []
    raw_payloads = []
    calc_payloads = []

    cat_name = niche_stats.get("category_name", "未知品类")
    cat_sales = niche_stats.get("sale_qty", 0)
    cat_product_count = niche_stats.get("sale_product_qty", 1)
    cat_ratio = cat_sales / cat_product_count if cat_product_count > 0 else 0
    cat_path = " > ".join([c["category_name"] for c in niche_stats.get("up_categories_json", [])])

    print(f"[SYNC] 正在同步 {len(products)} 条商品详情至 V2.0 数据库...")

    for p in products:
        sku = str(p.get('product_code'))
        m_sales = int(p.get('sale_qty', 0))
        m_amount = float(p.get('sale_amount', 0))
        reviews = int(p.get('review_qty', 0))
        price = float(p.get('sale_price', 0))
        
        # 计算评分 (完全对齐图 1 评分规范)
        s_sales = ScoringEngine.score_monthly_sales(m_sales)
        s_reviews = ScoringEngine.score_reviews(reviews)
        s_price = ScoringEngine.score_price(price)
        
        # 单品均销得分 (NEW)
        s_avg_sales = ScoringEngine.score_avg_sales_per_listing(cat_ratio)
        
        created_dt_str = p.get('created_dt')
        days_since_creation = 0
        if created_dt_str:
            try:
                dt = datetime.strptime(created_dt_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                days_since_creation = (datetime.now() - dt).days
            except: pass
        
        s_days_per_review = ScoringEngine.score_days_per_review(days_since_creation, reviews)
        
        # 总分加和
        total_score = s_sales + s_reviews + s_price + s_avg_sales + s_days_per_review

        # 构造 Raw Payload (对齐 V2.0 Schema)
        raw_payloads.append({
            "sku": sku,
            "task_id": final_task_id,
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
            "restrict_type": p.get('restrict_type'),
            "last_sale_date": p.get('last_sale_date')
            # 暂时移除分项得分同步，因为数据库表结构未对齐，会导致 upsert 报错
        })

        # 构造 Calc Payload
        calc_payloads.append({
            "sku": sku,
            "task_id": final_task_id,
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

    # 批量同步至 Supabase (化整为零，防止 SSL 超时)
    BATCH_SIZE = 25
    if raw_payloads:
        try:
            print(f"[SYNC] 正在分批同步 {len(raw_payloads)} 条商品数据 (每批 {BATCH_SIZE} 条)...")
            for i in range(0, len(raw_payloads), BATCH_SIZE):
                raw_chunk = raw_payloads[i:i + BATCH_SIZE]
                calc_chunk = calc_payloads[i:i + BATCH_SIZE]
                
                supabase.table("products_raw_data").upsert(raw_chunk).execute()
                supabase.table("products_calculated_metrics").upsert(calc_chunk).execute()
                print(f"  [SYNC] 已完成第 {i//BATCH_SIZE + 1} 批同步...")
            
            print(f"[SUCCESS] 数据库全量同步完成！")
        except Exception as e:
            print(f"[ERROR] 数据库同步失败: {e}")

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
        print(f"[SUCCESS] Excel 已生成: {output_path}")
        return output_path
    except Exception as e:
        print(f"[ERROR] Excel 导出失败: {e}")

if __name__ == "__main__":
    tid = sys.argv[1] if len(sys.argv) > 1 else None
    ifile = sys.argv[2] if len(sys.argv) > 2 else None
    process_rpa_data(tid, ifile)
