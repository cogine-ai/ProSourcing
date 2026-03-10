import asyncio
import os
import io
import sys
from playwright.async_api import async_playwright

async def capture_screenshot():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        
        context_args = {}
        if os.path.exists(storage_state):
            context_args['storage_state'] = storage_state
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        urls = ["https://app.algatop.kz/niche", "https://app.algatop.kz/markets-analytics"]
        
        for url in urls:
            print(f"Capturing {url}...")
            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(5)
                name = url.split("/")[-1]
                path = f"d:/item/ProSourcing/screenshot_{name}.png"
                await page.screenshot(path=path, full_page=True)
                print(f"Saved screenshot: {path}")
            except Exception as e:
                print(f"Failed to capture {url}: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_screenshot())
