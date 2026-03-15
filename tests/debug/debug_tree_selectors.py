import asyncio
import json
import os
import io
import sys
from playwright.async_api import async_playwright

async def debug_tree_selectors():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        context_args = {}
        if os.path.exists(storage_state):
            context_args['storage_state'] = storage_state
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        print("Loading /niche...")
        await page.goto("https://app.algatop.kz/niche", wait_until="domcontentloaded")
        await asyncio.sleep(8)
        
        # 找到“Телефоны и гаджеты”所在的行，看看它周围有啥
        elements = await page.evaluate('''() => {
            const target = Array.from(document.querySelectorAll('*')).find(e => e.innerText === 'Телефоны и гаджеты');
            if (!target) return "NOT FOUND";
            
            const parent = target.parentElement;
            const siblings = Array.from(parent.children).map(e => ({
                tag: e.tagName,
                className: e.className,
                text: e.innerText,
                html: e.outerHTML.substring(0, 100)
            }));
            
            const grandparent = parent.parentElement;
            const gp_siblings = Array.from(grandparent.children).map(e => ({
                tag: e.tagName,
                className: e.className,
                text: e.innerText,
                html: e.outerHTML.substring(0, 100)
            }));
            
            return { siblings, gp_siblings };
        }''')
        
        print(json.dumps(elements, indent=2, ensure_ascii=False))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_tree_selectors())
