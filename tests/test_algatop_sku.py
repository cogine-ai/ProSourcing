import asyncio
import os
import sys
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.algatop_scraper import AlgatopScraper

async def test_sku_fetch(sku):
    scraper = AlgatopScraper()
    await scraper.init_browser(headless=False)
    
    # Needs login to ensure we have access
    await scraper.login()
    
    url = f"https://app.algatop.kz/niche/product/{sku}"
    print(f"Navigating to {url}")
    await scraper.page.goto(url)
    
    # Wait for data to load
    await asyncio.sleep(5)
    
    # Take screenshot
    screenshot_path = f"d:/item/ProSourcing/output/{sku}_page.png"
    await scraper.page.screenshot(path=screenshot_path, full_page=True)
    print(f"Saved screenshot to {screenshot_path}")
    
    # Get HTML
    content = await scraper.page.content()
    with open(f"d:/item/ProSourcing/output/{sku}_page.html", "w", encoding="utf-8") as f:
        f.write(content)
        
    await scraper.close()

if __name__ == "__main__":
    asyncio.run(test_sku_fetch("134193498"))
