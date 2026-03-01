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
# 核心配置
# ==========================================
SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TEMPLATE_PATH = "d:/item/ProSourcing/AI产品开发.xlsx"
OUTPUT_DIR = "d:/item/ProSourcing/output"
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

def run_scoring_and_export(category_name="无人机"):
    print(f"\n--- 正在运行 {category_name} 评分与导出流程 ---")
    
    # 1. 从 Supabase 获取原始数据
    response = supabase.table("products_raw_data").select("*").order("created_at", desc=True).limit(50).execute()
    raw_products = response.data
    if not raw_products:
        print("错误: 数据库中未发现任何产品数据。")
        return

    # 2. 计算评分并准备结果
    processed_results = []
    for p in raw_products:
        sku = p['sku']
        sales_3m = p.get('sales_3m') or 0
        monthly_sales = sales_3m / 3.0  # 评分引擎按月销计
        reviews = p.get('reviews_count') or 0
        price = float(p.get('price') or 0)
        
        # 计算各分项得分
        m_score = ScoringEngine.score_monthly_sales(monthly_sales)
        r_score = ScoringEngine.score_reviews(reviews)
        p_score = ScoringEngine.score_price(price)
        
        # 处理日期计算比值
        listing_date_str = p.get('listing_date')
        days_per_review_score = 0
        days_diff = 90 # 默认 90 天
        if listing_date_str:
            try:
                dt = datetime.strptime(listing_date_str, "%Y-%m-%d")
                days_diff = (datetime.now() - dt).days
                days_per_review_score = ScoringEngine.score_days_per_review(days_diff, reviews)
            except: pass

        total_score = m_score + r_score + p_score + days_per_review_score
        
        # 类目统计比值
        cat_total_products = p.get('category_total_products') or 1
        sales_ratio = monthly_sales / cat_total_products if cat_total_products > 0 else 0
        
        # CR3 计算 (如果 top3_sales_sum 存在)
        cat_total_sales = p.get('category_total_sales') or 1
        cr3 = (p.get('top3_sales_sum') or 0) / cat_total_sales if cat_total_sales > 0 else 0

        # 指标回写准备
        calc_metric = {
            "sku": sku,
            "monthly_sales_score": float(m_score),
            "reviews_score": float(r_score),
            "price_score": float(p_score),
            "sales_to_products_ratio": float(sales_ratio),
            "days_to_reviews_ratio": float(days_per_review_score), # 这里存分值或比值，按 PRD
            "cr3_ratio": float(cr3),
            "total_score": float(total_score)
        }
        
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
        ws.cell(row=i, column=2, value=p.get('category_tree') or "未分类")
        
        # 下载图片并插入
        img_path = download_image(p.get('image_url'), p['sku'])
        if img_path:
            try:
                img = OpenPyxlImage(img_path)
                img.width, img.height = 70, 70
                ws.add_image(img, f"C{i}")
            except: ws.cell(row=i, column=3, value="图片下载失败")
        
        ws.cell(row=i, column=4, value=int(p.get('sales_3m', 0)/3))
        ws.cell(row=i, column=5, value=p.get('reviews_count'))
        ws.cell(row=i, column=6, value=f"{p.get('price')} ₸")
        ws.cell(row=i, column=7, value=p['sales_ratio_val'])
        ws.cell(row=i, column=8, value=p.get('listing_date'))
        ws.cell(row=i, column=9, value=p['final_total_score']) # 这里简化，按您表格逻辑填总分或分项
        ws.cell(row=i, column=10, value=p['cr3_val'])
        ws.cell(row=i, column=11, value=p.get('product_url'))
        ws.cell(row=i, column=12, value="详见 Algatop")
        ws.cell(row=i, column=13, value=p['final_total_score'])

    wb.save(output_path)
    print(f"\n✅ 导出成功: {output_path}")
    return output_path

if __name__ == "__main__":
    run_scoring_and_export("无人机")
