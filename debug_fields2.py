import asyncio
import os
from playwright.async_api import async_playwright

TEST_SKU = "113455666"  # 马桶刷

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx_args = {}
        if os.path.exists("d:/item/ProSourcing/auth.json"):
            ctx_args['storage_state'] = "d:/item/ProSourcing/auth.json"
        ctx = await browser.new_context(**ctx_args)
        page = await ctx.new_page()

        url = f"https://app.algatop.kz/niche/product/{TEST_SKU}"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)

        text = await page.inner_text("body", timeout=5000)
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # 重点输出 "Продавцов" 附近行
        print("=== Around Продавцов ===")
        for i, l in enumerate(lines):
            if "Продавцов" in l or "Отзывов" in l or "Рейтинг" in l:
                print(f"  [{i-2}] {lines[i-2] if i>=2 else ''}")
                print(f"  [{i-1}] {lines[i-1] if i>=1 else ''}")
                print(f"  [{i}] >> {l}")
                print(f"  [{i+1}] {lines[i+1] if i+1<len(lines) else ''}")
                print(f"  [{i+2}] {lines[i+2] if i+2<len(lines) else ''}")
                print()

        print("=== Around Продажи/Выручка ===")
        for i, l in enumerate(lines):
            if "Продажи" in l or "Выручка" in l or "дням" in l or "месячно" in l:
                print(f"  [{i-1}] {lines[i-1] if i>=1 else ''}")
                print(f"  [{i}] >> {l}")
                print(f"  [{i+1}] {lines[i+1] if i+1<len(lines) else ''}")
                print(f"  [{i+2}] {lines[i+2] if i+2<len(lines) else ''}")
                print()

        # 现在切换到月视图，然后切换到3个月时间范围
        print("\n=== Clicking 'Помесячно' button ===")
        monthly_btn = page.locator("text=Помесячно")
        if await monthly_btn.count() > 0:
            await monthly_btn.first.click()
            await asyncio.sleep(3)
            print("Clicked Помесячно!")
        else:
            print("Помесячно button not found")

        # 检查是否有日期选择器，尝试输入3个月范围
        print("\n=== Looking for date picker ===")
        date_inputs = await page.locator("input[type='date'], input[placeholder*='дата'], input[placeholder*='дат']").all()
        print(f"Found {len(date_inputs)} date inputs")

        date_pickers = await page.locator(".date-picker, .DatePicker, [class*='date'], [class*='calendar']").all()
        print(f"Found {len(date_pickers)} date picker elements")

        # 检查当前页面日期范围显示
        text2 = await page.inner_text("body", timeout=5000)
        lines2 = [l.strip() for l in text2.split('\n') if l.strip()]
        print("\n=== Around Продажи (after switch) ===")
        for i, l in enumerate(lines2):
            if "Продажи" in l or "Выручка" in l:
                for j in range(max(0,i-1), min(len(lines2), i+4)):
                    print(f"  [{j}] {lines2[j]}")
                print()
                break  # Just first occurrence

        # Navigate to category page
        cat_links = await page.locator('a[href*="/niche/category/"]').all()
        if cat_links:
            cat_href = await cat_links[-1].get_attribute("href")
            cat_url = f"https://app.algatop.kz{cat_href}" if cat_href.startswith("/") else cat_href
            print(f"\n=== Navigating to category: {cat_url} ===")
            await page.goto(cat_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(6)

            c_text = await page.inner_text("body", timeout=5000)
            c_lines = [l.strip() for l in c_text.split('\n') if l.strip()]

            print("=== First 60 lines of CATEGORY page ===")
            for i, l in enumerate(c_lines[:60]):
                print(f"  [{i:3d}] {l}")

            # CR3 table lines
            print("\n=== Row texts for CR3 ===")
            rows = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('div[role="row"], tr, [class*="row"], [class*="Row"]')).slice(0,10).map(e => e.innerText.trim().substring(0,200));
            }''')
            for i, r in enumerate(rows):
                if r:
                    print(f"Row[{i}]: {r[:200]}")

        await browser.close()

asyncio.run(debug())
