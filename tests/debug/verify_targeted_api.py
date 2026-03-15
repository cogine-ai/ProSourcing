import asyncio
import json
import os
import io
import sys
import datetime
from playwright.async_api import async_playwright

async def verify_targeted_api():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        
        # 必须先建立域名上下文
        await page.goto("https://app.algatop.kz/niche", wait_until="commit", timeout=60000)
        await asyncio.sleep(5)
        
        end_date = datetime.date.today().strftime("%Y%m%d")
        start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y%m%d")
        
        # 使用 Subagent 嗅探到的有效 ID 00126 (Гаджеты)
        test_id = "00126"
        api_url = f"/api/v1/niche/categoryListStatistic?startDate={start_date}&endDate={end_date}&categoryId={test_id}"
        
        print(f"Testing Targeted API: {api_url}")
        
        result = await page.evaluate(f'''async () => {{
            try {{
                const res = await fetch("{api_url}", {{
                    headers: {{
                        "top-l": "2s3dfnfRgn43PkgmPolqre#"
                    }}
                }});
                const data = await res.json();
                return {{ ok: res.ok, status: res.status, data: data }};
            }} catch (e) {{
                return {{ error: e.message }};
            }}
        }}''')
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 顺便检查一下根目录到底返回啥
        root_url = f"/api/v1/niche/categoryListStatistic?startDate={start_date}&endDate={end_date}"
        root_result = await page.evaluate(f'''async () => {{
            const res = await fetch("{root_url}", {{
                headers: {{ "top-l": "2s3dfnfRgn43PkgmPolqre#" }}
            }});
            return await res.json();
        }}''')
        print("\nRoot API Result Sample:")
        items = root_result.get("data", [])
        print(f"Found {len(items)} items at root.")
        if items:
            for item in items[:5]:
                print(f"  {item.get('categoryName') or item.get('category_name')}: {item.get('categoryId') or item.get('category_id')}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_targeted_api())
