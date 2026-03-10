import asyncio
import json
import os
import io
import sys
import datetime
from playwright.async_api import async_playwright

async def debug_api():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        
        print("Connecting to Algatop...")
        try:
            await page.goto("https://app.algatop.kz/", wait_until="commit", timeout=60000)
        except:
            print("Navigation timed out, but proceeding to API check...")
        
        end_date = datetime.date.today().strftime("%Y%m%d")
        start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y%m%d")
        
        # 调试 ROOT 请求
        api_url = f"/api/v1/niche/categoryListStatistic?startDate={start_date}&endDate={end_date}"
        print(f"Testing API: {api_url}")
        
        result = await page.evaluate(f'''async () => {{
            try {{
                const res = await fetch("{api_url}");
                const data = await res.json();
                return {{ ok: res.ok, status: res.status, data: data }};
            }} catch (e) {{
                return {{ error: e.message }};
            }}
        }}''')
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_api())
