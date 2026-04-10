import asyncio
from playwright.async_api import async_playwright
import os

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use existing storage state if available
        storage_state_path = "d:/item/ProSourcing/auth.json"
        
        context_args = {}
        if os.path.exists(storage_state_path):
            context_args['storage_state'] = storage_state_path
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()

        print("--- Inspecting Algatop Product ---")
        try:
            await page.goto("https://app.algatop.kz/niche/product/134193498", timeout=60000)
            
            # Wait a bit for the page to render
            await asyncio.sleep(5)
            
            html = await page.content()
            with open("d:/item/ProSourcing/output/algatop_product_dom.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"Saved Algatop product HTML ({len(html)} bytes).")
            
            # Take a screenshot
            await page.screenshot(path="d:/item/ProSourcing/output/algatop_product.png", full_page=True)
            print("Saved Algatop product screenshot.")
            
        except Exception as e:
            print(f"Error inspecting Algatop: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
