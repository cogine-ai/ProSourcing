import asyncio
from playwright.async_api import async_playwright
import os

async def test_extract():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state_path = "d:/item/ProSourcing/auth.json"
        
        context_args = {}
        if os.path.exists(storage_state_path):
            context_args['storage_state'] = storage_state_path
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        url = "https://app.algatop.kz/niche/product/134193498"
        print(f"Navigating to {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(8)

            
            # Save HTML
            html = await page.content()
            with open("d:/item/ProSourcing/output/debug_134193498.html", "w", encoding="utf-8") as f:
                f.write(html)
                
            # Print page text
            text = await page.inner_text("body")
            with open("d:/item/ProSourcing/output/debug_134193498.txt", "w", encoding="utf-8") as f:
                f.write(text)
                
            print("Saved debug outputs.")
            
        except Exception as e:
            print(f"Error: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_extract())
