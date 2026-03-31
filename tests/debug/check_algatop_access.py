import asyncio
import json
import os
import io
import sys
from playwright.async_api import async_playwright

async def check_access():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        
        try:
            await page.goto("https://app.algatop.kz/niche", wait_until="commit", timeout=60000)
        except:
            print("Navigation timed out, proceeding to API check...")
        
        # 探测是否有权限
        access = await page.evaluate('''async () => {
            const res = await fetch("/api/v1/niche/access");
            return await res.json();
        }''')
        
        print("Access Response:")
        print(json.dumps(access, indent=2, ensure_ascii=False))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_access())
