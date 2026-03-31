import asyncio
import json
import os
import io
import sys
from playwright.async_api import async_playwright

async def inspect_elements():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        context_args = {}
        if os.path.exists(storage_state):
            context_args['storage_state'] = storage_state
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        print("Loading /niche to inspect elements...")
        await page.goto("https://app.algatop.kz/niche", wait_until="domcontentloaded")
        await asyncio.sleep(8)
        
        # Capture all links
        links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a')).map(a => ({
                text: a.innerText.trim(),
                href: a.getAttribute('href'),
                className: a.className
            }));
        }''')
        
        # Capture all toggles/buttons
        toggles = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.v-treeview-node__toggle, .v-icon, button, .mdi')).map(e => ({
                tag: e.tagName,
                text: e.innerText.trim(),
                className: e.className,
                style: e.getAttribute('style')
            }));
        }''')
        
        with open("d:/item/ProSourcing/inspect_elements.json", "w", encoding="utf-8") as f:
            json.dump({"links": links, "toggles": toggles}, f, ensure_ascii=False, indent=2)
        
        print(f"Captured {len(links)} links and {len(toggles)} potential toggles.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_elements())
