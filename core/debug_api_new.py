import asyncio
import json
import os
import io
import sys
import datetime
from playwright.async_api import async_playwright

async def debug_api_new_account():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        
        # 跳转建立上下文
        await page.goto("https://app.algatop.kz/niche", wait_until="commit", timeout=60000)
        await asyncio.sleep(5)
        
        end_date = datetime.date.today().strftime("%Y%m%d")
        start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y%m%d")
        
        # 探测 00002
        api_url = f"/api/v1/niche/categoryListStatistic?startDate={start_date}&endDate={end_date}&categoryId=00002"
        print(f"Testing API with new account: {api_url}")
        
        result = await page.evaluate(f'''async () => {{
            try {{
                const res = await fetch("{api_url}");
                const data = await res.json();
                return {{ ok: res.ok, status: res.status, data: data }};
            }} catch (e) {{
                return {{ error: e.message }};
            }}
        }}''')
        
        print("\n--- API Response Detail ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 也尝试一下不带 categoryId 的情况
        api_root_url = f"/api/v1/niche/categoryListStatistic?startDate={start_date}&endDate={end_date}"
        print(f"\nTesting Root API: {api_root_url}")
        root_result = await page.evaluate(f'''async () => {{
            try {{
                const res = await fetch("{api_root_url}");
                const data = await res.json();
                return data;
            }} catch (e) {{
                return {{ error: e.message }};
            }}
        }}''')
        print(json.dumps(root_result, indent=2, ensure_ascii=False)[:1000]) # 只看前 1000 字符

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_api_new_account())
