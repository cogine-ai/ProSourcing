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
        ws = wb.active
    except Exception as e:
        print(f"Error loading template: {e}")
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        # Set headers if template is missing/corrupt
        headers = ['文件生成时间', '产品类目树', '产品首图', '月销数量', '评论数量', '产品售价', '产品 所在细分类目的月销/该细分类目下的产品总数的比值', '上架时间', '上架时间距离当下时间间隔的天数/评论数的比值', 'CR3', '产品链接', '该细分类目下近6个月的销量曲线图', '得分总和']
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=h)
    
    start_row = ws.max_row + 1
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for i, p in enumerate(products, start=start_row):
        sku = p.get('sku', f"unknown_{i}")
        
        # 1. 下载首图
        img_url = p.get('image_url', "")
        img_path = get_image_path(img_url, sku, "d:/item/ProSourcing/output/images")
        
        # 2. 查找曲线图 (Algatop)
        chart_path = f"d:/item/ProSourcing/output/charts/chart_{sku}.png"
        
        # 3. 填充基础数据
        ws.cell(row=i, column=1, value=now_str)
        ws.cell(row=i, column=2, value="Спорт и отдых > Йога > Коврики")
        # 留空 C 列给首图
        
        # 月销数量如果是0，做预估
        reviews = int(p.get('reviews', 0))
        sales = p.get('sales')
        if not sales:
            sales = reviews * 3 if reviews > 0 else 0
            
        ws.cell(row=i, column=4, value=sales)
        ws.cell(row=i, column=5, value=reviews)
        ws.cell(row=i, column=6, value=p.get('price', "0"))
        ws.cell(row=i, column=7, value="分析中(缺类目总数)")
        ws.cell(row=i, column=8, value=p.get('listing_date', "N/A"))
        
        days_per_review = p.get('scores', {}).get('days_per_review_score', "N/A")
        if p.get('listing_date', "N/A") != "N/A":
             # 这里可以实际计算，暂时用 score
             pass
             
        ws.cell(row=i, column=9, value=days_per_review)
        ws.cell(row=i, column=10, value=p.get('cr3', "N/A"))
        ws.cell(row=i, column=11, value="https://kaspi.kz" + p.get('url', ""))
        # 留空 L 列给曲线图
        ws.cell(row=i, column=13, value=p.get('total_score', 0))
        
        # 4. 插入图片
        ws.row_dimensions[i].height = 60 # 设置行高
        
        if img_path and os.path.exists(img_path):
            img = Image(img_path)
            img.width, img.height = 60, 60
            ws.add_image(img, f"C{i}")
            ws.column_dimensions['C'].width = 12
            
        if os.path.exists(chart_path):
            chart_img = Image(chart_path)
            # 缩放到合适大小
            chart_img.width, chart_img.height = 120, 60
            ws.add_image(chart_img, f"L{i}")
            ws.column_dimensions['L'].width = 20
        else:
            ws.cell(row=i, column=12, value="无数据")
            
    wb.save(output_path)
    print(f"Excel report successfully generated with images at {output_path}")

if __name__ == "__main__":
    json_path = "d:/item/ProSourcing/output/enriched_results.json"
    template_path = "d:/item/ProSourcing/AI产品开发.xlsx"
    output_path = "d:/item/ProSourcing/output/Yoga_Mat_Analysis_Report_v2.xlsx"
    
    if not os.path.exists(json_path):
        # 降级使用 Kaspi 结果
        json_path = "d:/item/ProSourcing/output/kaspi_results.json"
        
    export_to_excel(json_path, template_path, output_path)
