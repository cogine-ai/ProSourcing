import asyncio
import os
import io
import sys
from playwright.async_api import async_playwright

async def monitor_network():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        
        # 监听所有请求
        requests = []
        page.on("request", lambda request: requests.append({
            "url": request.url,
            "method": request.method,
            "headers": request.headers
        }))

        print("Navigating to Algatop and monitoring network...")
        try:
            await page.goto("https://app.algatop.kz/niche", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)
        except:
            print("Navigation had some issues, but checking captured requests...")

        # 过滤出可能是分类数据的 API
        api_requests = [r for r in requests if "/api/v1/" in r["url"]]
        
        print("\n--- Captured API Requests ---")
        for r in api_requests:
            print(f"[{r['method']}] {r['url']}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(monitor_network())
