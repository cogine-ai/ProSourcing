import asyncio
import os
import re
from playwright.async_api import async_playwright

# 测试 SKU: 112843341 (LARKO yogapurple1)
TEST_SKU = "112843341"

async def debug_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context_args = {}
        if os.path.exists("d:/item/ProSourcing/auth.json"):
            context_args['storage_state'] = "d:/item/ProSourcing/auth.json"
        ctx = await browser.new_context(**context_args)
        page = await ctx.new_page()
        
        url = f"https://app.algatop.kz/niche/product/{TEST_SKU}"
        print(f"Navigating to {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)
        
        # 截取页面完整文本，每行打印便于观察
        text = await page.inner_text("body", timeout=5000)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        print("\n=== FULL PAGE TEXT (filtered) ===")
        for i, line in enumerate(lines):
            print(f"[{i:3d}] {line}")
        
        # 专门检查销量相关字段
        print("\n=== SALES RELATED SEARCH ===")
        for pattern in ["Продажи", "Продаж", "шт", "Выручка", "₸", "продавцов", "продавца", "Появилось"]:
            idxs = [i for i, l in enumerate(lines) if pattern in l]
            if idxs:
                for i in idxs:
                    print(f"[{pattern}] line {i}: {lines[i]}")
                    if i+1 < len(lines): print(f"  next: {lines[i+1]}")
                    if i+2 < len(lines): print(f"  +2: {lines[i+2]}")
        
        # 保存完整 HTML 供分析
        html = await page.content()
        with open("d:/item/ProSourcing/output/debug_algatop_112843341.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("\nHTMl saved to output/debug_algatop_112843341.html")
        
        await browser.close()

asyncio.run(debug_page())
