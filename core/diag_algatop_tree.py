import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        storage_state = "d:/item/ProSourcing/auth.json"
        
        context_args = {}
        if os.path.exists(storage_state):
            print(f"Using storage state: {storage_state}")
            context_args['storage_state'] = storage_state
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        print("Navigating to https://app.algatop.kz/niche ...")
        
        # Listen for API responses
        async def handle_response(response):
            if "algatop.kz/api" in response.url:
                print(f"API CALL: {response.url} | {response.status}")
                if "category" in response.url.lower():
                    try:
                        data = await response.json()
                        print(f"  [DATA] {str(data)[:200]}...")
                    except:
                        pass
                        
        page.on("response", handle_response)
        
        await page.goto("https://app.algatop.kz/niche", wait_until="networkidle")
        await asyncio.sleep(10)
        
        # Look for category tree links
        links = await page.locator('a[href*="/niche/category/"]').all()
        print(f"\nFound {len(links)} category links in initial load:")
        for i, link in enumerate(links[:20]):
            href = await link.get_attribute("href")
            text = await link.inner_text()
            print(f"  {i+1}: {text} -> {href}")
            
        # Check if there's a specific "tree" container
        # Typical classes for trees include 'v-treeview', 'tree', etc.
        tree_els = await page.locator('.v-treeview, .tree-container, .niche-tree').all()
        print(f"\nFound {len(tree_els)} tree containers.")
        
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
