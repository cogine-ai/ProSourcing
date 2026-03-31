import json
import os
import requests
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.drawing.image import Image
from openpyxl.utils import get_column_letter

def get_image_path(url, sku, folder):
    if not url:
        return None
    try:
        os.makedirs(folder, exist_ok=True)
        img_path = os.path.join(folder, f"{sku}.jpg")
        if not os.path.exists(img_path):
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with open(img_path, 'wb') as f:
                    f.write(response.content)
            else:
                return None
        return img_path
    except Exception as e:
        print(f"Error downloading image for {sku}: {e}")
        return None

def export_to_excel(json_path, template_path, output_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if isinstance(data, list):
        products = data
    else:
        products = data.get("products", [])
        
    try:    
        wb = load_workbook(template_path)
        ws1 = wb.active
        ws1.title = "指标评分"
    except Exception as e:
        print(f"Error loading template: {e}")
        from openpyxl import Workbook
        wb = Workbook()
        ws1 = wb.active
        ws1.title = "指标评分"
        # Set headers if template is missing/corrupt
        headers = ['文件生成时间', '产品类目树', '产品首图', '月销数量', '评论数量', '产品售价', '销品比', '上架时间', '上架天数', 'CR3', '产品链接', '趋势', '得分总和']
        for col, h in enumerate(headers, 1):
            ws1.cell(row=1, column=col, value=h)
    
    start_row = ws1.max_row + 1
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 哥，这里是“指标评分”页的填充逻辑 (按照选品报告指标部分校准)
    for i, p in enumerate(products, start=start_row):
        sku = p.get('sku', p.get('product_code', f"unknown_{i}"))
        
        # 1. 下载首图
        img_url = p.get('image_url', "")
        if not img_url and 'preview_image_list' in p:
            try:
                imgs = p['preview_image_list']
                if isinstance(imgs, str): imgs = json.loads(imgs)
                if imgs: img_url = imgs[0].get('large')
            except: pass

        img_path = get_image_path(img_url, sku, "d:/item/ProSourcing/output/images")
        
        # 3. 填充基础数据
        ws1.cell(row=i, column=1, value=now_str)
        ws1.cell(row=i, column=2, value=p.get('category_name', p.get('cat_path', "Unknown")))
        # C 列留给图，D 列留给链接
        ws1.cell(row=i, column=4, value=p.get('url', p.get('product_url', "")))
        
        # 指标评分部分 (Sheet 1 展示得分)
        ws1.cell(row=i, column=5, value=p.get('s_sales', 0))
        ws1.cell(row=i, column=6, value=p.get('s_reviews', 0))
        ws1.cell(row=i, column=7, value=p.get('s_price', 0))
        ws1.cell(row=i, column=8, value=p.get('s_days_per_review', 0))
        ws1.cell(row=i, column=9, value=p.get('s_avg_sales', 0))
        ws1.cell(row=i, column=10, value=p.get('cr3', "N/A"))
        ws1.cell(row=i, column=11, value=p.get('total_score', 0))
        
        # 4. 插入图片
        ws1.row_dimensions[i].height = 80 # 设置行高
        
        if img_path and os.path.exists(img_path):
            img = Image(img_path)
            img.width, img.height = 100, 100
            ws1.add_image(img, f"C{i}")
            ws1.column_dimensions['C'].width = 15
            
    # --- Sheet 2: 原始商品数据 ---
    ws2 = wb.create_sheet("原始商品数据")
    raw_headers = ["SKU", "商品名称", "品牌", "售价", "评论数", "月销量", "创建时间", "链接"]
    for col, h in enumerate(raw_headers, 1):
        ws2.cell(row=1, column=col, value=h)
        
    for i, p in enumerate(products, start=2):
        ws2.cell(row=i, column=1, value=p.get('sku', p.get('product_code')))
        ws2.cell(row=i, column=2, value=p.get('product_name', p.get('name')))
        ws2.cell(row=i, column=3, value=p.get('brand_name', p.get('brand')))
        ws2.cell(row=i, column=4, value=p.get('sale_price', p.get('price')))
        ws2.cell(row=i, column=5, value=p.get('review_qty', p.get('reviews')))
        ws2.cell(row=i, column=6, value=p.get('sale_qty', p.get('monthly_sales')))
        ws2.cell(row=i, column=7, value=p.get('created_dt', p.get('listing_date')))
        ws2.cell(row=i, column=8, value=p.get('product_url', p.get('url')))

    wb.save(output_path)
    print(f"Excel report successfully generated with images at {output_path}")

if __name__ == "__main__":
    json_path = "d:/item/ProSourcing/output/json/enriched_results.json"
    template_path = "d:/item/ProSourcing/templates/AI产品开发.xlsx"
    output_path = "d:/item/ProSourcing/output/excel/Yoga_Mat_Analysis_Report_v2.xlsx"
    
    if not os.path.exists(json_path):
        # 降级使用 Kaspi 结果
        json_path = "d:/item/ProSourcing/output/json/kaspi_results.json"
        
    export_to_excel(json_path, template_path, output_path)
