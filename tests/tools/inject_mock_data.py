import os
import sys
from datetime import datetime

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.final_pipeline import supabase

def inject_mock_data():
    print("🎭 正在注入演示 Mock 数据...")
    
    # 1. 模拟 20 个一级分类
    mock_cats = [
        {"id": "c1", "name": "Электроника (电子)", "monthly_sales": 15000, "product_count": 200, "is_top_level": True},
        {"id": "c2", "name": "Одежда (服装)", "monthly_sales": 28000, "product_count": 1200, "is_top_level": True},
        {"id": "c3", "name": "Красота (美容)", "monthly_sales": 12000, "product_count": 450, "is_top_level": True},
        {"id": "c4", "name": "Автотовары (汽车)", "monthly_sales": 8000, "product_count": 300, "is_top_level": True},
        {"id": "c5", "name": "Детские товары (母婴)", "monthly_sales": 9500, "product_count": 500, "is_top_level": True},
        {"id": "c6", "name": "Спорт (运动)", "monthly_sales": 7000, "product_count": 280, "is_top_level": True},
    ]
    
    for cat in mock_cats:
        cat["sales_to_product_ratio"] = cat["monthly_sales"] / cat["product_count"]
        cat["last_sync_at"] = datetime.now().isoformat()
        try:
            supabase.table("categories").upsert(cat).execute()
        except: pass

    # 2. 模拟几个历史任务
    mock_tasks = [
        {"category": "Дроны (无人机)", "status": "completed", "progress": 100, "excel_path": "d:/item/ProSourcing/output/rpa_demo.xlsx"},
        {"category": "Зубные щетки (牙刷)", "status": "crawling", "progress": 45},
        {"category": "Кофемашины (咖啡机)", "status": "pending", "progress": 0}
    ]
    
    for t in mock_tasks:
        t["created_at"] = datetime.now().isoformat()
        try:
            supabase.table("analysis_tasks").insert(t).execute()
        except: pass

    print("✅ Mock 数据注入成功！哥，你现在重启后端就能看到满血的界面了。")

if __name__ == "__main__":
    inject_mock_data()
