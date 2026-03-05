import asyncio
import json
import os
import sys
from datetime import datetime

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.algatop_rpa_scraper import AlgatopRPAScraper
from core.final_pipeline import supabase

async def sync_all_categories():
    print("🚀 开始同步品类大盘数据...")
    rpa = AlgatopRPAScraper()
    connected = await rpa.connect()
    
    if not connected:
        print("❌ 无法连接到浏览器，请确保已经启动 launch_rpa_chrome.py 并登录。")
        return

    await rpa.setup_listeners()
    
    print("\n💡 正在获取一级分类统计数据...")
    # 模拟访问一级分类聚合页面以触发 API (此处需要根据实际 URL 调整)
    # 假设访问这个 URL 会触发 categoryListStatistic 接口
    await rpa.page.goto("https://app.algatop.kz/niche/category")
    await asyncio.sleep(5) # 等待数据捕获
    
    categories = rpa.captured_data.get("categories", [])
    if not categories:
        print("⚠️ 未截获到一级分类数据，请检查浏览器是否停留在分类页面。")
        await rpa.pw.stop()
        return

    print(f"✅ 捕获到 {len(categories)} 个一级分类。正在写入数据库...")

    # 处理并写入一级分类 (Top 20 逻辑)
    for cat in categories:
        cat_id = cat.get("category_id")
        sales = cat.get("sale_qty", 0)
        products = cat.get("sale_product_qty", 1)
        ratio = sales / products if products > 0 else 0
        
        db_data = {
            "id": cat_id,
            "name": cat.get("category_name"),
            "monthly_sales": sales,
            "product_count": products,
            "sales_to_product_ratio": ratio,
            "is_top_level": True,
            "last_sync_at": datetime.now().isoformat()
        }
        
        try:
            supabase.table("categories").upsert(db_data).execute()
        except Exception as e:
            print(f"  [DB Error] 分类 {cat_id} 写入失败: {e}")

    print("\n✅ 品类大盘同步完成！现在前端首页可以展示 20 个一级分类了。")
    await rpa.pw.stop()

if __name__ == "__main__":
    asyncio.run(sync_all_categories())
