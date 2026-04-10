import asyncio
import sys
import os
from deep_translator import GoogleTranslator

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrapers.kaspi_scraper import KaspiScraper

async def test_dynamic_search(category):
    print(f"--- TEST: Input '{category}' ---")
    
    # 逻辑同 server.py
    search_keyword = category
    try:
        if any('\u4e00' <= char <= '\u9fff' for char in category):
            translator = GoogleTranslator(source='auto', target='ru')
            search_keyword = translator.translate(category)
            print(f"--- Translated to: '{search_keyword}' ---")
    except Exception as e:
        print(f"--- Translation Error: {e} ---")

    scraper = KaspiScraper()
    await scraper.init_browser(headless=True)
    
    print(f"--- Searching Kaspi for '{search_keyword}' ---")
    products = await scraper.search_products(search_keyword, limit=3)
    
    print("\n--- FINAL VERIFICATION RESULTS ---")
    if not products:
        print("❌ NO PRODUCTS FOUND")
    for i, p in enumerate(products):
        print(f"[{i+1}] TITLE: {p['title']}")
    
    await scraper.close()

if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "键盘"
    asyncio.run(test_dynamic_search(kw))
