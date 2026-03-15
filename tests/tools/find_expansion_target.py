import asyncio
import json
import os
import io
import sys
from playwright.async_api import async_playwright

async def find_expansion_target():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        context_args = {}
        if os.path.exists(storage_state):
            context_args['storage_state'] = storage_state
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        print("Loading /niche to find the expansion target...")
        await page.goto("https://app.algatop.kz/niche", wait_until="domcontentloaded")
        await asyncio.sleep(8)
        
        # 探测：寻找“Телефоны и гаджеты”并分析它左边或右边的可点击元素
        analysis = await page.evaluate('''() => {
            const findText = (text) => {
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                let node;
                while(node = walker.nextNode()) {
                    if (node.textContent.includes(text)) return node.parentElement;
                }
                return null;
            };

            const target = findText('Телефоны и гаджеты');
            if (!target) return { error: 'Text not found' };

            // 往上找几层父级，看看哪一层有“小箭头”
            let results = [];
            let current = target;
            for (let i = 0; i < 5; i++) {
                if (!current) break;
                const siblings = Array.from(current.parentElement.children).map(s => ({
                    tag: s.tagName,
                    className: s.className,
                    text: s.innerText,
                    html: s.outerHTML.substring(0, 200),
                    isClickable: window.getComputedStyle(s).cursor === 'pointer'
                }));
                results.push({
                    level: i,
                    tag: current.tagName,
                    className: current.className,
                    siblings: siblings
                });
                current = current.parentElement;
            }
            return results;
        }''')
        
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
        
        # 顺便看看有没有类似 svg 的图标
        icons = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('svg, i, .v-icon')).map(e => ({
                tag: e.tagName,
                className: e.className,
                path: e.innerHTML.substring(0, 100)
            })).slice(0, 20);
        }''')
        print("\nIcon samples:")
        print(json.dumps(icons, indent=2, ensure_ascii=False))
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_expansion_target())
