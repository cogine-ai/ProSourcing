import asyncio
import os
import io
import sys
from playwright.async_api import async_playwright

async def debug_html():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Headless is fine for HTML dump
        storage_state = "d:/item/ProSourcing/auth.json"
        context_args = {}
        if os.path.exists(storage_state):
            context_args['storage_state'] = storage_state
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        print("Fetching /niche HTML...")
        await page.goto("https://app.algatop.kz/niche", wait_until="domcontentloaded")
        await asyncio.sleep(8)
        
        content = await page.content()
        with open("d:/item/ProSourcing/debug_niche.html", "w", encoding="utf-8") as f:
            f.write(content)
        
        print("HTML saved to debug_niche.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_html())
