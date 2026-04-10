
import asyncio
import os
import sys
from dotenv import load_dotenv

# 确保导入路径正确
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.algatop_scraper import AlgatopScraper
from scrapers.kaspi_scraper import KaspiScraper

async def run_integration_test():
    load_dotenv()
    
    # 1. 初始化爬虫
    kaspi = KaspiScraper(storage_state_path=None)
    algatop = AlgatopScraper(storage_state_path="auth.json")
    
    await kaspi.init_browser(headless=True)
    await algatop.init_browser(headless=True)
    
    try:
        # 2. 从 Kaspi 获取 SKU
        keyword = "коврик для йоги"
        print(f"--- Step 1: Searching Kaspi for '{keyword}' ---")
        products = await kaspi.search_products(keyword, limit=3)
        if not products:
            print("No products found on Kaspi.")
            return

        sample_sku = products[0]['sku']
        print(f"Sample SKU from Kaspi: {sample_sku}")

        # 3. 登录 Algatop 并识别 Niche
        print(f"--- Step 2: Identifying Niche on Algatop for SKU {sample_sku} ---")
        await algatop.login()
        niche_name = await algatop.search_niche_by_sku(sample_sku)
        
        if niche_name:
            print(f"Successfully identified niche: {niche_name}")
            # 这里后续可以扩展为提取该 Niche 的详细数据
        else:
            print("Failed to identify niche.")

    except Exception as e:
        print(f"Integration test failed: {e}")
    finally:
        await kaspi.close()
        await algatop.close()

if __name__ == "__main__":
    asyncio.run(run_integration_test())
