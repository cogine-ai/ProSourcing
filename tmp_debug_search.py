import asyncio
import urllib.parse
import sys
import os

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrapers.kaspi_scraper import KaspiScraper

async def debug_search(category):
    # 同步 server.py 的翻译逻辑
    TRANSMAP = {
        "杯子": "кружка",
        "电动牙刷": "электрическая зубная щетка",
        "无人机": "дрон",
        "键盘": "клавиатура",
        "鼠标": "мышь"
    }
    search_keyword = TRANSMAP.get(category.strip(), category)
    print(f"--- DEBUG: Category '{category}' -> Translated: '{search_keyword}' ---")
    
    scraper = KaspiScraper()
    await scraper.init_browser(headless=True)
    
    products = await scraper.search_products(search_keyword, limit=5)
    print("\nResults found:")
    for i, p in enumerate(products):
        print(f"[{i+1}] {p['title']} (SKU: {p['sku']})")
    
    await scraper.close()

if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "杯子"
    asyncio.run(debug_search(kw))
