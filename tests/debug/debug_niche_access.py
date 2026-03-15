import asyncio
import os
import io
import sys
from playwright.async_api import async_playwright

async def debug_niche():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        
        url = "https://app.algatop.kz/niche"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(8)
        
        print(f"Current URL: {page.url}")
        
        # 截图看状态
        screenshot_path = "d:/item/ProSourcing/output/niche_debug.png"
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        # 检查有没有 a 标签
        links_count = await page.locator('a').count()
        print(f"Total links on page: {links_count}")
        
        category_links = await page.locator('a[href*="/niche/category/"]').all()
        print(f"Category links detected: {len(category_links)}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_niche())
