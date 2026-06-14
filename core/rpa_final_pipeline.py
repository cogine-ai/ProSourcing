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
import concurrent.futures

# ==========================================
# 核心配置
# ==========================================
INPUT_FILE = "./output/json/rpa_output.json"
TEMPLATE_PATH = "./templates/AI产品开发.xlsx"
OUTPUT_DIR = "./output"
# 优先从环境变量读取，避免图片入包导致项目臃肿
IMAGE_DIR = os.getenv("IMAGE_STORAGE_PATH", os.path.join(OUTPUT_DIR, "images"))
os.makedirs(IMAGE_DIR, exist_ok=True)

def download_image(url, sku):
    """支持并行下载，增加超时控制和重试策略"""
    if not url: return None
    path = os.path.join(IMAGE_DIR, f"{sku}.jpg")
    if os.path.exists(path): return path
    try:
        # 哥，超时时间缩短为 5s，如果是内网或断网没必要死等
        r = requests.get(url, timeout=5)
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

from core.rpa_category_id import resolve_niche_category_id


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
    target_file = input_file or os.path.join(OUTPUT_DIR, "json", f"rpa_output_{task_id}.json")
    
    if not os.path.exists(target_file):
        print(f"[ERROR] 找不到输入文件: {target_file}")
        sys.exit(1)

    with open(target_file, "r", encoding="utf-8") as f:
        rpa_data = json.load(f)

    niche_stats = rpa_data.get("niche_stats", {})
    products = rpa_data.get("products", [])[:160]  # 哥，本次多页采集同步 160 条 (8页)
    trend = rpa_data.get("trend", [])

    # 哥，针对分类层级的汉化增强逻辑：不再保留俄文，直接从 master 表查中文直替
    up_cats = niche_stats.get("up_categories_json") or []
    if up_cats:
        try:
            all_up_ids = [str(cat.get("category_id")) for cat in up_cats]
            if ENV_MOD == "production":
                cur_tmp = conn.cursor()
                query_up = "SELECT algatop_id, name_cn FROM algatop_categories_master WHERE algatop_id IN %s"
                cur_tmp.execute(query_up, (tuple(all_up_ids),))
                cn_rows = cur_tmp.fetchall()
                cur_tmp.close()
                cn_map_l10n = {str(r[0]): r[1] for r in cn_rows if r[1]}
            else:
                res_tmp = supabase.table("algatop_categories_master").select("algatop_id, name_cn").in_("algatop_id", all_up_ids).execute()
                cn_map_l10n = {str(r['algatop_id']): r['name_cn'] for r in res_tmp.data if r.get('name_cn')}

            for cat in up_cats:
                cid_str = str(cat.get("category_id"))
                if cid_str in cn_map_l10n:
                    cat["category_name"] = cn_map_l10n[cid_str]
            
            print(f"[L10N] 已完成分类层级汉化直替: {[c['category_name'] for c in up_cats]}")
        except Exception as e:
            print(f"[WARN] 分类层级汉化直替失败: {e}")

    if not products:
        print("[ERROR] 商品列表为空，请检查采集环节。")
        return

    # 翻译商品名称 (哥，客户现场环境可能没网，暂时注掉)
    # from deep_translator import GoogleTranslator
    # import concurrent.futures

    # def translate_name(p):
    #     raw_name = p.get('product_name')
    #     if not raw_name: return p
    #     try:
    #         # 哥，源语言定死为 'ru' (俄语)，提高翻译准确度和稳定性
    #         translator = GoogleTranslator(source='ru', target='zh-CN')
    #         p['product_name'] = translator.translate(raw_name)
    #         # print(f"[DEBUG] Translated: {raw_name[:20]} -> {p['product_name'][:20]}")
    #     except Exception as e:
    #         print(f"[WARN] 翻译失败 ({raw_name[:20]}...): {e}")
    #         pass
    #     return p

    # print(f"[SYNC] 正在翻译 {len(products)} 条商品名称...")
    # with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    #     products = list(executor.map(translate_name, products))

    # 1.1 校验 Task ID，如果无效则创建新任务
    final_task_id = task_id
    if not is_valid_uuid(task_id):
        print(f"[INFO] Task ID '{task_id}' 无效，正在数据库中创建新任务...")
        new_task_data = {
            "category": f"RPA采集_{niche_stats.get('category_name', '未知')}_{datetime.now().strftime('%m%d_%H%M')}",
            "status": "completed",
            "category_id": resolve_niche_category_id(niche_stats),
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
        brand_count_original = niche_stats.get("sale_brand_qty") or 0
        
        # 哥，确保汇总数和总数都有值，别让前端显示 "--"
        if not niche_stats.get("sale_product_qty"):
            niche_stats["sale_product_qty"] = len(products)
            
        # CR3 计算 (爬取前三之和 / Algatop大盘总销售额)
        cr3_ratio = (top3_revenue / total_revenue_original * 100) if total_revenue_original and total_revenue_original > 0 else 0
        
        # 把这些核心值同步到 niche_stats，确保前端绑定简单
        niche_stats["top3_revenue"] = top3_revenue
        niche_stats["sale_amount"] = total_revenue_original
        niche_stats["brand_qty"] = brand_count_original
        niche_stats["sale_merchant_qty"] = niche_stats.get("sale_seller_qty") or 0
        niche_stats["cr3"] = f"{cr3_ratio:.1f}%"
        niche_stats["valid_product_count"] = 0 # 占位，稍后由循环统计覆盖
        
        print(f"[STATS] 指标校准：Top3={top3_revenue}, 品牌数(原装)={brand_count_original}, 卖家数={niche_stats['sale_merchant_qty']}, CR3={niche_stats['cr3']}, 总产品数={niche_stats['sale_product_qty']}")

    cat_sales = niche_stats.get("sale_qty") or 0
    cat_product_count = niche_stats.get("sale_product_qty") or 0
    cat_ratio = cat_sales / cat_product_count if cat_product_count and cat_product_count > 0 else 0
    cat_path = " > ".join([c["category_name"] for c in (niche_stats.get("up_categories_json") or [])])

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

    valid_product_count = 0
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

        # 哥，计算有效产品数（符合潜力优质筛选标准：销量>=60, 评论>=15, 价格>=800, 天数<=300）
        if m_sales >= 60 and reviews >= 15 and price >= 800 and days_since_creation <= 300:
            valid_product_count += 1

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
            "total_score": total_score, "cat_path": cat_path,
            # 哥，存一下各项因子得分，Sheet 1 要用
            "s_sales": s_sales, "s_reviews": s_reviews, "s_price": s_price,
            "s_days_per_review": s_days_per_review, "s_avg_sales": s_avg_sales
        })

    # 哥，把最终统计的有效数塞进大盘数据
    niche_stats["valid_product_count"] = valid_product_count
    print(f"[STATS] 有效产品数统计完成: {valid_product_count}")

    # 批量同步至数据库 (环境分流)
    if raw_payloads:
        try:
            if ENV_MOD == "production":
                print(f"[SYNC] 正在同步 {len(raw_payloads)} 条数据至本地 PostgreSQL...")
                cursor = conn.cursor()
                
                # Schema PK is products_raw_data(sku) — not (sku, task_id)
                raw_query = """INSERT INTO products_raw_data (sku, task_id, product_name, brand_name, gen_brand_id, product_url, sale_price, product_rate, review_qty, merchant_count, sale_qty, sale_amount, amount_abc, amount_prc, preview_image_list, created_dt, category_name, category_ext_id, restrict_type, last_sale_date) 
                               VALUES %s ON CONFLICT (sku) DO UPDATE SET task_id = EXCLUDED.task_id, product_name = EXCLUDED.product_name, brand_name = EXCLUDED.brand_name, gen_brand_id = EXCLUDED.gen_brand_id, product_url = EXCLUDED.product_url, sale_price = EXCLUDED.sale_price, product_rate = EXCLUDED.product_rate, review_qty = EXCLUDED.review_qty, merchant_count = EXCLUDED.merchant_count, sale_qty = EXCLUDED.sale_qty, sale_amount = EXCLUDED.sale_amount, amount_abc = EXCLUDED.amount_abc, amount_prc = EXCLUDED.amount_prc, preview_image_list = EXCLUDED.preview_image_list, created_dt = EXCLUDED.created_dt, category_name = EXCLUDED.category_name, category_ext_id = EXCLUDED.category_ext_id, restrict_type = EXCLUDED.restrict_type, last_sale_date = EXCLUDED.last_sale_date"""
                
                raw_values = [(p['sku'], p['task_id'], p['product_name'], p['brand_name'], p['gen_brand_id'], p['product_url'], p['sale_price'], p['product_rate'], p['review_qty'], p['merchant_count'], p['sale_qty'], p['sale_amount'], p['amount_abc'], p['amount_prc'], p['preview_image_list'], p['created_dt'], p['category_name'], p['category_ext_id'], p['restrict_type'], p['last_sale_date']) for p in raw_payloads]
                execute_values(cursor, raw_query, raw_values)
                
                # 同步计算指标
                calc_query = "INSERT INTO products_calculated_metrics (sku, task_id, total_score) VALUES %s ON CONFLICT (sku) DO UPDATE SET task_id = EXCLUDED.task_id, total_score = EXCLUDED.total_score"
                calc_values = [(p['sku'], p['task_id'], p['total_score']) for p in calc_payloads]
                execute_values(cursor, calc_query, calc_values)
                
                # 更新 Task 汇总信息
                final_update = {
                    "category_id": resolve_niche_category_id(niche_stats),
                    "category_stats": json.dumps(json_safe(niche_stats), ensure_ascii=False),
                    "trend_data": json.dumps(json_safe(trend), ensure_ascii=False),
                    "up_categories": json.dumps(json_safe(niche_stats.get("up_categories_json")), ensure_ascii=False),
                    "id": final_task_id
                }
                # 哥，这儿得显式带上 ID，防止 psycopg2 报错
                cursor.execute("UPDATE analysis_tasks SET category_id=%(category_id)s, category_stats=%(category_stats)s, trend_data=%(trend_data)s, up_categories=%(up_categories)s, status='completed' WHERE id=%(id)s", final_update)
                
                conn.commit()
                cursor.close()
                print(f"[SUCCESS] 本地 PostgreSQL 业务数据同步完成！")
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
                    "category_id": resolve_niche_category_id(niche_stats),
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
    # 哥，文件名格式：分类名_日期
    now_date = datetime.now().strftime('%Y%m%d')
    output_filename = f"{cat_name}_{now_date}.xlsx"
    
    # 哥，文件夹不存在的话保存会炸，咱们得先建好
    excel_dir = os.path.join(OUTPUT_DIR, "excel")
    os.makedirs(excel_dir, exist_ok=True)
    output_path = os.path.join(excel_dir, output_filename)
    
    try:
        from openpyxl import Workbook
        wb = Workbook()
        
        # --- Sheet 1: 指标评分 (核心分析表) ---
        ws1 = wb.active
        ws1.title = "指标评分"
        # 哥，按照您的最新要求调整字段
        headers1 = ['日期', '品类', '图', '链接', '月销评分', '评论评分', '售价评分', '上架天数/评论比值评分', '销品比评分', 'CR3集中度', '总得分']
        for col, h in enumerate(headers1, 1):
            ws1.cell(row=1, column=col, value=h)
        
        cr3_val = niche_stats.get('cr3', 'N/A')
        
        # --- 哥，高能预警：开始并行下载 160 张图片，由于是断网高发区，这里开 15 个线程顶住 ---
        print(f"[SYNC] 正在并行下载 {len(processed_results)} 张商品图片 (15 Threads)...")
        img_tasks = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            # 建立 SKU 到图片的映射，方便后续插入 Sheet
            future_to_sku = {executor.submit(download_image, p['image_url'], p['sku']): p['sku'] for p in processed_results}
            sku_to_local_path = {}
            for future in concurrent.futures.as_completed(future_to_sku):
                sku = future_to_sku[future]
                try:
                    sku_to_local_path[sku] = future.result()
                except:
                    sku_to_local_path[sku] = None
        
        for i, p in enumerate(processed_results, start=2):
            ws1.row_dimensions[i].height = 80 # 大图展示
            ws1.cell(row=i, column=1, value=datetime.now().strftime("%Y-%m-%d"))
            ws1.cell(row=i, column=2, value=p['cat_path'])
            
            # 链接 (移到前面)
            ws1.cell(row=i, column=4, value=p['url'])
            
            # 从刚才并行下载的 Map 里直接拿路径，不再串行等待
            img_path = sku_to_local_path.get(p['sku'])
            if img_path:
                try:
                    img = OpenPyxlImage(img_path)
                    img.width, img.height = 100, 100
                    ws1.add_image(img, f"C{i}")
                except:
                    ws1.cell(row=i, column=3, value="图片损坏")
            else:
                ws1.cell(row=i, column=3, value="下载失败/无网")
            
            # 这里需要各个子评分，由于前面循环里没存，这里重新算一下或者从 processed_results 结构里取
            # 哥，我回头在前面循环把子评分也塞进 processed_results 里，这里先直接取
            ws1.cell(row=i, column=5, value=p.get('s_sales', 0))
            ws1.cell(row=i, column=6, value=p.get('s_reviews', 0))
            ws1.cell(row=i, column=7, value=p.get('s_price', 0))
            ws1.cell(row=i, column=8, value=p.get('s_days_per_review', 0))
            ws1.cell(row=i, column=9, value=p.get('s_avg_sales', 0))
            ws1.cell(row=i, column=10, value=cr3_val) # CR3 是类目维度的
            ws1.cell(row=i, column=11, value=p['total_score'])

        # --- Sheet 2: 原始商品数据 ---
        ws2 = wb.create_sheet("原始商品数据")
        raw_headers = ["SKU", "商品名称", "品牌", "售价", "评分", "评论数", "商家数", "月销量", "月销售额", "上架日期", "类目名称", "链接"]
        for col, h in enumerate(raw_headers, 1):
            ws2.cell(row=1, column=col, value=h)
            
        for i, r in enumerate(raw_payloads, start=2):
            ws2.cell(row=i, column=1, value=r['sku'])
            ws2.cell(row=i, column=2, value=r['product_name'])
            ws2.cell(row=i, column=3, value=r['brand_name'])
            ws2.cell(row=i, column=4, value=r['sale_price'])
            ws2.cell(row=i, column=5, value=r['product_rate'])
            ws2.cell(row=i, column=6, value=r['review_qty'])
            ws2.cell(row=i, column=7, value=r['merchant_count'])
            ws2.cell(row=i, column=8, value=r['sale_qty'])
            ws2.cell(row=i, column=9, value=r['sale_amount'])
            ws2.cell(row=i, column=10, value=r['created_dt'])
            ws2.cell(row=i, column=11, value=r['category_name'])
            ws2.cell(row=i, column=12, value=r.get('product_url', ''))

        wb.save(output_path)
        print(f"[SUCCESS] Excel 已生成（指标评分校准完成）: {output_path}")

        # 哥，最关键一步：把生成的 Excel 路径同步回数据库，前端下载按钮才能亮起来
        # 注意此处的路径要对齐 API 下载接口 (相对路径)
        try:
            rel_path = f"output/excel/{output_filename}"
            if ENV_MOD == "production":
                cursor = conn.cursor()
                cursor.execute("UPDATE analysis_tasks SET excel_path=%s WHERE id=%s", (rel_path, final_task_id))
                conn.commit()
                cursor.close()
                print(f"[SYNC] Excel 路径已关联至数据库 (PG)")
            else:
                supabase.table("analysis_tasks").update({"excel_path": rel_path}).eq("id", final_task_id).execute()
                print(f"[SYNC] Excel 路径已关联至数据库 (Supabase)")
        except Exception as se:
            print(f"[WARN] 关联 Excel 路径失败: {se}")

        return output_path
    except Exception as e:
        print(f"[ERROR] Excel 导出失败: {e}")

if __name__ == "__main__":
    tid = sys.argv[1] if len(sys.argv) > 1 else None
    ifile = sys.argv[2] if len(sys.argv) > 2 else None
    process_rpa_data(tid, ifile)
