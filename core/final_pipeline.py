import json
import os
import sys
import re
import requests
from datetime import datetime
from supabase import create_client, Client
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenPyxlImage

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.scoring import ScoringEngine

# ==========================================
# 核心配置 (环境分流)
# ==========================================
ENV_MOD = os.getenv("ENV_MOD", "development")
SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"

class PGQueryBuilder:
    """每个查询都是独立的实例，彻底解决并发带来的状态污染问题。"""
    def __init__(self, conn_url, table_name):
        self.conn_url = conn_url
        self._table = table_name
        self._where = []
        self._order = None
        self._limit = None
        self._offset = None
        self._update_data = None
        self._upsert = False
        self._count_mode = None

    def select(self, columns="*", count=None):
        self._count_mode = count
        return self

    def insert(self, data):
        self._update_data = data
        return self

    def update(self, data):
        self._update_data = data
        return self
    
    def upsert(self, data):
        self._update_data = data
        self._upsert = True
        return self

    def order(self, column, desc=True):
        self._order = f"{column} {'DESC' if desc else 'ASC'}"
        return self

    def limit(self, n):
        self._limit = n
        return self

    def offset(self, n):
        self._offset = n
        return self

    def eq(self, col, val):
        self._where.append((col, val))
        return self
    
    def in_(self, col, vals):
        self._where.append((col, vals, 'IN'))
        return self

    def range(self, start, end):
        self._offset = start
        self._limit = (end - start + 1)
        return self

    def ilike(self, col, val):
        self._where.append((col, val, 'ILIKE'))
        return self

    def execute(self):
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(self.conn_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            if self._update_data is not None:
                data_list = [self._update_data] if isinstance(self._update_data, dict) else self._update_data
                results = []
                for item in data_list:
                    keys = list(item.keys())
                    if self._upsert:
                        columns = ", ".join(keys)
                        placeholders = ", ".join(["%s"] * len(keys))
                        update_stmt = ", ".join([f"{k}=EXCLUDED.{k}" for k in keys if k != 'sku' and k != 'id'])
                        pk = "sku" if "sku" in keys else "id"
                        query = f"INSERT INTO {self._table} ({columns}) VALUES ({placeholders}) ON CONFLICT ({pk}) DO UPDATE SET {update_stmt} RETURNING *"
                        cursor.execute(query, tuple(item.values()))
                    elif self._where:
                        set_stmt = ", ".join([f"{k}=%s" for k in keys])
                        where_stmt = " AND ".join([f"{w[0]}=%s" for w in self._where])
                        query = f"UPDATE {self._table} SET {set_stmt} WHERE {where_stmt} RETURNING *"
                        cursor.execute(query, tuple(item.values()) + tuple(w[1] for w in self._where))
                    else:
                        columns = ", ".join(keys)
                        placeholders = ", ".join(["%s"] * len(keys))
                        query = f"INSERT INTO {self._table} ({columns}) VALUES ({placeholders}) RETURNING *"
                        cursor.execute(query, tuple(item.values()))
                    if cursor.description:
                        results.append(cursor.fetchone())
                conn.commit()
                data = results
            else:
                where_clauses = []
                params = []
                for w in self._where:
                    if len(w) == 3 and w[2] == 'IN':
                        where_clauses.append(f"{w[0]} = ANY(%s)")
                        params.append(list(w[1]))
                    elif len(w) == 3 and w[2] == 'ILIKE':
                        where_clauses.append(f"{w[0]} ILIKE %s")
                        params.append(w[1])
                    else:
                        where_clauses.append(f"{w[0]} = %s")
                        params.append(w[1])
                
                where_str = ""
                if where_clauses:
                    where_str = " WHERE " + " AND ".join(where_clauses)

                if self._count_mode == 'exact':
                    query = f"SELECT COUNT(*) FROM {self._table}" + where_str
                    cursor.execute(query, tuple(params))
                    row = cursor.fetchone()
                    count_val = row['count'] if row and 'count' in row else 0
                    from collections import namedtuple
                    Response = namedtuple('Response', ['data', 'count'])
                    return Response(data=[], count=count_val)

                query = f"SELECT * FROM {self._table}" + where_str
                if self._order: query += f" ORDER BY {self._order}"
                if self._limit: query += f" LIMIT {self._limit}"
                if self._offset: query += f" OFFSET {self._offset}"
                
                cursor.execute(query, tuple(params))
                data = cursor.fetchall()
            
            from collections import namedtuple
            Response = namedtuple('Response', ['data', 'count'])
            return Response(data=data, count=len(data))
        finally:
            cursor.close()
            conn.close()

class PGSupabaseShim:
    """哥，这是一个针对生产环境 PostgreSQL 的 Supabase 语法兼容层。"""
    def __init__(self, conn_url):
        self.conn_url = conn_url

    def table(self, table_name):
        return PGQueryBuilder(self.conn_url, table_name)

# 初始化
if ENV_MOD == "production":
    PG_URL = os.getenv("DATABASE_URL", "postgresql://postgres:prosourcing123@db:5432/prosourcing")
    print(f"[INIT] 生产环境：正在初始化 PostgreSQL 兼容层...")
    supabase = PGSupabaseShim(PG_URL)
else:
    print(f"[INIT] 开发环境：正在连接 Supabase 云端...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TEMPLATE_PATH = "./AI产品开发.xlsx"
OUTPUT_DIR = "./output"
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
os.makedirs(IMAGE_DIR, exist_ok=True)

def download_image(url, sku):
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

def run_scoring_and_export(category_name="无人机", task_id=None):
    print(f"\n--- 正在运行 {category_name} 评分与导出流程 (Task: {task_id}) ---")
    
    # 1. 从 Supabase 获取原始数据
    query = supabase.table("products_raw_data").select("*")
    
    # 哥，咱们得先拿到任务的全局统计信息，不然销品比算不准
    cat_stats = {}
    if task_id:
        task_res = supabase.table("analysis_tasks").select("category_stats").eq("id", task_id).execute()
        if task_res.data:
            try:
                stats_json = task_res.data[0].get("category_stats")
                if isinstance(stats_json, str): stats_json = json.loads(stats_json)
                cat_stats = stats_json or {}
            except: pass

    if task_id:
        query = query.eq("task_id", task_id)
    else:
        query = query.order("created_at", desc=True).limit(50)
    
    response = query.execute()
    raw_products = response.data
    if not raw_products:
        print("错误: 数据库中未发现任何产品数据。")
        return

    # 2. 计算评分并准备结果
    processed_results = []
    for p in raw_products:
        sku = p['sku']
        # 哥，字段得对齐生产环境：sale_qty 是 30 天销量
        monthly_sales = float(p.get('sale_qty') or 0)
        reviews = int(p.get('review_qty') or 0)
        price = float(p.get('sale_price') or 0)
        
        # 计算各分项得分
        m_score = ScoringEngine.score_monthly_sales(monthly_sales)
        r_score = ScoringEngine.score_reviews(reviews)
        p_score = ScoringEngine.score_price(price)
        
        # 处理日期计算比值
        listing_date_str = p.get('created_dt')
        days_per_review_score = 0
        days_diff = 90 # 默认 90 天
        if listing_date_str:
            try:
                # 兼容不同格式
                if ' ' in listing_date_str: dt_str = listing_date_str.split(' ')[0]
                else: dt_str = listing_date_str
                dt = datetime.strptime(dt_str, "%Y-%m-%d")
                days_diff = (datetime.now() - dt).days
                days_per_review_score = ScoringEngine.score_days_per_review(days_diff, reviews)
            except: pass

        total_score = m_score + r_score + p_score + days_per_review_score
        
        # 类目统计比值 (优先用从任务里拿到的全局大盘数据)
        cat_total_products = cat_stats.get('sale_product_qty') or p.get('category_total_products') or 1
        sales_ratio = monthly_sales / cat_total_products if cat_total_products > 0 else 0
        
        # CR3 计算
        cat_total_sales = cat_stats.get('sale_amount') or p.get('category_total_sales') or 1
        # 如果 p 里没有 top3，这里暂时用 0 或从 cat_stats 找
        top3_val = cat_stats.get('top3_revenue') or p.get('top3_sales_sum') or 0
        cr3 = top3_val / cat_total_sales if cat_total_sales > 0 else 0

        # 指标回写准备 (哥，只存总分，分项得分在 Excel 里看)
        calc_metric = {
            "sku": sku,
            "task_id": task_id,
            "total_score": float(total_score)
        }
        if task_id:
            calc_metric["task_id"] = task_id
        
        # 这里我们就顺手写回 Supabase
        try:
            supabase.table("products_calculated_metrics").upsert(calc_metric).execute()
        except Exception as e:
            print(f"  [DB WARNING] SKU {sku} 指标写入失败: {e}")

        # 挂载额外信息用于 Excel
        p['final_total_score'] = total_score
        p['cr3_val'] = f"{cr3*100:.1f}%"
        p['sales_ratio_val'] = f"{sales_ratio*100:.4f}%"
        p['days_diff'] = days_diff
        processed_results.append(p)

    # 按总分排序
    processed_results.sort(key=lambda x: x['final_total_score'], reverse=True)

    # 3. 导出到 Excel
    output_filename = f"{category_name}_选品调研报告_{datetime.now().strftime('%m%d')}.xlsx"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    try:
        wb = load_workbook(TEMPLATE_PATH)
        ws = wb.active
    except:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        headers = ['文件生成时间', '产品类目树', '产品首图', '月销数量', '评论数量', '产品售价', '月销/类目产品总数比', '上架时间', '上架天数/评论数得分', 'CR3', '链接', '月销曲线', '总分']
        for col, h in enumerate(headers, 1): ws.cell(row=1, column=col, value=h)

    start_row = 2 # 从第二行开始写或追写
    now_str = datetime.now().strftime("%Y-%m-%d")

    for i, p in enumerate(processed_results, start=start_row):
        ws.row_dimensions[i].height = 65
        ws.cell(row=i, column=1, value=now_str)
        ws.cell(row=i, column=2, value=p.get('category_tree') or p.get('category_name') or "未分类")
        
        # 下载图片并插入 (解析 JSON 列表，增强鲁棒性)
        img_url = ""
        try:
            imgs = p.get('preview_image_list')
            if isinstance(imgs, str): imgs = json.loads(imgs)
            if isinstance(imgs, list) and len(imgs) > 0:
                first_img = imgs[0]
                # 哥，针对 Algatop 不同的字段名做兼容搜寻
                img_url = (first_img.get('large') or 
                           first_img.get('gallery-large') or 
                           first_img.get('gallery') or 
                           first_img.get('medium') or 
                           "")
        except: pass

        img_path = download_image(img_url, p['sku'])
        if img_path:
            try:
                img = OpenPyxlImage(img_path)
                img.width, img.height = 70, 70
                ws.add_image(img, f"C{i}")
            except: ws.cell(row=i, column=3, value="图片下载失败")
        
        ws.cell(row=i, column=4, value=int(p.get('sale_qty') or 0))
        ws.cell(row=i, column=5, value=p.get('review_qty'))
        ws.cell(row=i, column=6, value=f"{p.get('sale_price')} ₸")
        ws.cell(row=i, column=7, value=p['sales_ratio_val'])
        ws.cell(row=i, column=8, value=p.get('created_dt'))
        ws.cell(row=i, column=9, value=p['final_total_score']) # 这里简化，按您表格逻辑填总分 or 分项
        ws.cell(row=i, column=10, value=p['cr3_val'])
        ws.cell(row=i, column=11, value=p.get('product_url'))
        ws.cell(row=i, column=12, value="详见 Algatop")
        ws.cell(row=i, column=13, value=p['final_total_score'])

    wb.save(output_path)
    print(f"\n✅ 导出成功: {output_path}")
    return output_path

if __name__ == "__main__":
    import sys
    # 哥，支持命令行传参，方便咱们手动重跑历史任务
    cat = sys.argv[1] if len(sys.argv) > 1 else "无人机"
    tid = sys.argv[2] if len(sys.argv) > 2 else None
    run_scoring_and_export(cat, tid)
