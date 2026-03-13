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
INPUT_FILE = "./output/rpa_output.json"
TEMPLATE_PATH = "./AI产品开发.xlsx"
OUTPUT_DIR = "./output"
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
# 核心处理逻辑 (含 V2.0 数据库同步 - 环境感知)
# ==========================================
from supabase import create_client, Client
import uuid

# 基础配置
ENV_MOD = os.getenv("ENV_MOD", "development")
SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"

# 初始化数据库连接 (环境分流)
if ENV_MOD == "production":
    import psycopg2
    from psycopg2.extras import execute_values
    PG_URL = os.getenv("DATABASE_URL", "postgresql://postgres:prosourcing123@db:5432/prosourcing")
    print(f"[INIT] 生产环境模式：正在连接本地 PostgreSQL...")
    conn = psycopg2.connect(PG_URL)
    supabase = None # 生产环境不强依赖 Supabase
else:
    print(f"[INIT] 开发环境模式：正在连接线上 Supabase...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    conn = None

def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except:
        return False

def json_safe(obj):
    """确保对象可以被 JSON 序列化，如果不可序列，返回 None。
    主要用于防止 coroutine、异步对象等被意外传入 Supabase JSONB 字段。
    """
    import inspect
    if obj is None:
        return None
    # 如果是协程，直接丢弃（不 await，因为已经脱离 async 上下文）
    if inspect.iscoroutine(obj):
        print(f"[WARN] json_safe: 检测到 coroutine 对象，已丢弃")
        obj.close()  # 防止 RuntimeWarning: coroutine was never awaited
        return None
    try:
        json.dumps(obj, ensure_ascii=False)
        return obj
    except (TypeError, ValueError) as e:
        print(f"[WARN] json_safe: 字段不可序列化，已置 None: {e}")
        return None

def process_rpa_data(task_id=None, input_file=None):
    # 如果没传 input_file，则尝试拼接默认路径
    # 哥，这里一定要统一用相对路径，不然容器里找不着
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

    # 1.1 校验 Task ID，如果无效则创建新任务
    final_task_id = task_id
    if not is_valid_uuid(task_id):
        print(f"[INFO] Task ID '{task_id}' 无效，正在数据库中创建新任务...")
        new_task_data = {
            "category": f"RPA采集_{niche_stats.get('category_name', '未知')}_{datetime.now().strftime('%m%d_%H%M')}",
            "status": "completed",
            "category_id": niche_stats.get("category_ext_id"),
            "category_stats": json.dumps(json_safe(niche_stats), ensure_ascii=False),
            "trend_data": json.dumps(json_safe(trend), ensure_ascii=False),
            "up_categories": json.dumps(json_safe(niche_stats.get("up_categories_json")), ensure_ascii=False)
        }
        
        if ENV_MOD == "production":
            cursor = conn.cursor()
            query = "INSERT INTO analysis_tasks (category, status, category_id, category_stats, trend_data, up_categories) VALUES (%(category)s, %(status)s, %(category_id)s, %(category_stats)s, %(trend_data)s, %(up_categories)s) RETURNING id"
            cursor.execute(query, new_task_data)
            final_task_id = str(cursor.fetchone()[0])
            conn.commit()
            cursor.close()
        else:
            res = supabase.table("analysis_tasks").insert(new_task_data).execute()
            if res.data: final_task_id = res.data[0]["id"]
            
        print(f"[SUCCESS] 已创建新任务: {final_task_id}")

    # 2. 处理商品数据并同步 (products_raw_data & products_calculated_metrics)
    processed_results = []
    raw_payloads = []
    calc_payloads = []

    cat_name = niche_stats.get("category_name", "未知品类")
    
    # 哥，指标这块儿咱们得严格分两路走：
    # 1. 大盘数据（销售总额、品牌数等）要“原封不动”用 Algatop 给的聚合字段
    # 2. 统计数据（前3名之和、CR3）则根据本次实际抓取的列表来算
    if products:
        # 计算前三名 (基于本次抓取的 160 条)
        sorted_by_revenue = sorted(products, key=lambda x: float(x.get('sale_amount', 0)), reverse=True)
        top3_products = sorted_by_revenue[:3]
        top3_revenue = sum(float(p.get('sale_amount', 0)) for p in top3_products)
        
        # 兜底：如果 Algatop 没给大盘销售额，我们才用列表求和
        total_revenue_original = niche_stats.get("sale_amount") 
        if total_revenue_original is None:
            total_revenue_original = sum(float(p.get('sale_amount', 0)) for p in products)
        
        # 品牌数：严格使用 Algatop 原始字段 (sale_brand_qty)
        brand_count_original = niche_stats.get("sale_brand_qty", 0)
        
        # CR3 计算 (爬取前三之和 / Algatop大盘总销售额)
        cr3_ratio = (top3_revenue / total_revenue_original * 100) if total_revenue_original > 0 else 0
        
        # 把这些核心值同步到 niche_stats，确保前端绑定简单
        niche_stats["top3_revenue"] = top3_revenue
        niche_stats["sale_amount"] = total_revenue_original
        niche_stats["brand_qty"] = brand_count_original
        niche_stats["sale_merchant_qty"] = niche_stats.get("sale_seller_qty", 0)
        niche_stats["cr3"] = f"{cr3_ratio:.1f}%"
        
        print(f"[STATS] 指标校准：Top3={top3_revenue}, 品牌数(原装)={brand_count_original}, 卖家数={niche_stats['sale_merchant_qty']}, CR3={niche_stats['cr3']}")

    cat_sales = niche_stats.get("sale_qty", 0)
    cat_product_count = niche_stats.get("sale_product_qty", 1)
    cat_ratio = cat_sales / cat_product_count if cat_product_count > 0 else 0
    cat_path = " > ".join([c["category_name"] for c in niche_stats.get("up_categories_json", [])])

    print(f"[SYNC] 正在同步 {len(products)} 条商品详情至 V2.0 数据库...")

    # 哥，针对类似 "80 000" 这种带空格的字符串，咱们得先清洗一下再转数字
    def safe_int(v):
        if v is None: return 0
        try: return int(str(v).replace(' ', '').replace(',', '').split('.')[0])
        except: return 0
    def safe_float(v):
        if v is None: return 0.0
        try: return float(str(v).replace(' ', '').replace(',', ''))
        except: return 0.0

    for p in products:
        sku = str(p.get('product_code'))
        m_sales = safe_int(p.get('sale_qty', 0))
        m_amount = safe_float(p.get('sale_amount', 0))
        reviews = safe_int(p.get('review_qty', 0))
        price = safe_float(p.get('sale_price', 0))
        
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
        
        # 总分加和 (月销量 + 评论 + 价格 + 销品比 + 成长潜力)
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
            "last_sale_date": p.get('last_sale_date'),
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

    # 批量同步至数据库 (环境分流)
    if raw_payloads:
        try:
            if ENV_MOD == "production":
                print(f"[SYNC] 正在同步 {len(raw_payloads)} 条数据至本地 PostgreSQL...")
                cursor = conn.cursor()
                
                # 同步原始数据
                raw_query = """INSERT INTO products_raw_data (sku, task_id, product_name, brand_name, gen_brand_id, product_url, sale_price, product_rate, review_qty, merchant_count, sale_qty, sale_amount, amount_abc, amount_prc, preview_image_list, created_dt, category_name, category_ext_id, restrict_type, last_sale_date) 
                               VALUES %s ON CONFLICT (sku) DO UPDATE SET task_id = EXCLUDED.task_id, sale_qty = EXCLUDED.sale_qty, sale_amount = EXCLUDED.sale_amount"""
                
                raw_values = [(p['sku'], p['task_id'], p['product_name'], p['brand_name'], p['gen_brand_id'], p['product_url'], p['sale_price'], p['product_rate'], p['review_qty'], p['merchant_count'], p['sale_qty'], p['sale_amount'], p['amount_abc'], p['amount_prc'], json.dumps(p['preview_image_list']), p['created_dt'], p['category_name'], p['category_ext_id'], p['restrict_type'], p['last_sale_date']) for p in raw_payloads]
                execute_values(cursor, raw_query, raw_values)
                
                # 同步计算指标
                calc_query = "INSERT INTO products_calculated_metrics (sku, task_id, total_score) VALUES %s ON CONFLICT (sku) DO UPDATE SET total_score = EXCLUDED.total_score"
                calc_values = [(p['sku'], p['task_id'], p['total_score']) for p in calc_payloads]
                execute_values(cursor, calc_query, calc_values)
                
                # 更新 Task 汇总信息
                final_update = {
                    "category_id": niche_stats.get("category_ext_id"),
                    "category_stats": json.dumps(json_safe(niche_stats), ensure_ascii=False),
                    "trend_data": json.dumps(json_safe(trend), ensure_ascii=False),
                    "up_categories": json.dumps(json_safe(niche_stats.get("up_categories_json")), ensure_ascii=False),
                    "id": final_task_id
                }
                cursor.execute("UPDATE analysis_tasks SET category_id=%(category_id)s, category_stats=%(category_stats)s, trend_data=%(trend_data)s, up_categories=%(up_categories)s, status='completed' WHERE id=%(id)s", final_update)
                
                conn.commit()
                cursor.close()
                print(f"[SUCCESS] 本地 PostgreSQL 同步完成！")
            else:
                # 保持原有的 Supabase 分批搬运逻辑
                BATCH_SIZE = 25
                print(f"[SYNC] 正在分批同步 {len(raw_payloads)} 条数据至 Supabase (每批 {BATCH_SIZE} 条)...")
                for i in range(0, len(raw_payloads), BATCH_SIZE):
                    raw_chunk = raw_payloads[i:i + BATCH_SIZE]
                    calc_chunk = calc_payloads[i:i + BATCH_SIZE]
                    supabase.table("products_raw_data").upsert(raw_chunk).execute()
                    supabase.table("products_calculated_metrics").upsert(calc_chunk).execute()
                
                final_update = {
                    "category_id": niche_stats.get("category_ext_id"),
                    "category_stats": json_safe(niche_stats),
                    "trend_data": json_safe(trend),
                    "up_categories": json_safe(niche_stats.get("up_categories_json")),
                    "status": "completed"
                }
                supabase.table("analysis_tasks").update(final_update).eq("id", final_task_id).execute()
                print(f"[SUCCESS] Supabase 同步完成！")
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
