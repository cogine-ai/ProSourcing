import asyncio
import json
import os
from playwright.async_api import async_playwright

async def capture_tree():
    async with async_playwright() as p:
        # 连接到用户已经登录的 Chrome
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        
        # 寻找已经在 /niche 的页面，或者新开一个
        page = None
        for p_page in context.pages:
            if "algatop.kz/niche" in p_page.url:
                page = p_page
                break
        
        if not page:
            print("No active /niche page found. Opening a new one...")
            page = await context.new_page()
            await page.goto("https://app.algatop.kz/niche")
        else:
            print(f"Found active page: {page.url}")
            # 刷新一下以确保抓到 API
            await page.reload()

        print("Waiting for categoryListStatistic API...")
        
        captured_json = None
        
        async def handle_response(response):
            nonlocal captured_json
            url = response.url
            if "algatop.kz/api" in url:
                print(f"Captured API: {url}")
                if "category" in url.lower():
                    print(f"Potential Category API: {url}")
                    if "List" in url or "tree" in url or "Statistic" in url:
                        try:
                            captured_json = await response.json()
                            print(f"Bingo! Captured from: {url}")
                        except:
                            pass

        page.on("response", handle_response)
        
        # 等待一段时间确保加载完成
        for _ in range(30):
            if captured_json:
                break
            await asyncio.sleep(1)
            
        if captured_json:
            output_path = "scripts/algatop_full_tree_v5.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(captured_json, f, ensure_ascii=False, indent=2)
            print(f"SUCCESS! Saved tree data to {output_path}")
            
            # 简单统计一下
            data = captured_json.get("data", {}).get("lines", [])
            print(f"Total categories found: {len(data)}")
        else:
            print("FAILED: Could not capture the tree API. Please ensure you are on the Niches page.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_tree())
