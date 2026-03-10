import asyncio
import json
import os
import io
import sys
from playwright.async_api import async_playwright

async def capture_live_seeds():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        
        print("Navigating to Algatop to capture seeds...")
        await page.goto("https://app.algatop.kz/niche", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5)
        
        # 抓取当前页面所有 category 链接
        seeds = await page.evaluate('''() => {
            const links = Array.from(document.querySelectorAll('a[href*="/niche/category/"]'));
            const map = {};
            links.forEach(l => {
                const match = l.href.match(/\/category\/(\d+)/);
                const text = l.innerText.trim();
                // 只要有文字且有 ID 就记下来
                if (match && text) {
                    map[text] = match[1];
                }
            });
            return map;
        }''')
        
        print(f"Captured {len(seeds)} seed categories:")
        for name, cid in seeds.items():
            print(f"  {name}: {cid}")
            
        output_path = "d:/item/ProSourcing/output/top_level_ids.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(seeds, f, ensure_ascii=False, indent=2)
            
        print(f"Saved to {output_path}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_live_seeds())
