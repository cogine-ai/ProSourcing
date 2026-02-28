import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

async def enrich_product(page, sku):
    url = f"https://app.algatop.kz/niche/product/{sku}"
    print(f"Enriching SKU {sku} through Algatop...")
    
    data = {
        "sales": 0,
        "listing_date": "N/A",
        "sellers": 0,
        "cr3": "N/A"
    }
    
    # 截图当作销量曲线图的一部分
    os.makedirs("d:/item/ProSourcing/output/charts", exist_ok=True)
    chart_path = f"d:/item/ProSourcing/output/charts/chart_{sku}.png"
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        # 等待页面渲染基本数据
        await asyncio.sleep(6)
        
        try:
            # 缩短超时时间，避免有的元素不显示导致卡死
            chart_el = page.locator("canvas, svg, .chart")
            if await chart_el.count() > 0:
                # 只等待 2 秒
                await chart_el.first.screenshot(path=chart_path, timeout=2000)
                print(f"[{sku}] Chart screenshot saved.")
            else:
                await page.screenshot(path=chart_path, clip={'x': 200, 'y': 200, 'width': 800, 'height': 400}, timeout=2000)
                print(f"[{sku}] Fallback screenshot saved.")
        except Exception as e:
            print(f"[{sku}] Chart screenshot failed: {e}. Trying fallback area.")
            try:
                await page.screenshot(path=chart_path, clip={'x': 200, 'y': 200, 'width': 800, 'height': 400}, timeout=2000)
            except:
                pass
            
        # 获取所有可见文本
        text = await page.inner_text("body", timeout=2000)
        
        # 使用正则表达式在宽泛文本中提取可能包含的数值
        if "Появился:" in text:
            match = re.search(r"Появился:\s*([\d-]+)", text)
            if match:
                data["listing_date"] = match.group(1)
                
        # 尝试提取 продавцов (卖家数量)
        match_sellers = re.search(r"(\d+)\s*продавцов", text)
        if match_sellers:
            data["sellers"] = match_sellers.group(1)
            
        # CR3 如果能看到的话，一般格式为 CR3 XX%
        match_cr3 = re.search(r"CR3[\s:]*([\d\.]+%)", text)
        if match_cr3:
            data["cr3"] = match_cr3.group(1)
                
        # ... other matches can be added here once we know the exact text format ...

    except Exception as e:
        print(f"Error enriching {sku}: {e}")
        
    return data

async def enrich_all():
    input_file = "d:/item/ProSourcing/output/kaspi_results.json"
    if not os.path.exists(input_file):
        print("Kaspi results not found.")
        return
        
    with open(input_file, "r", encoding="utf-8") as f:
        products = json.load(f)
        
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state_path = "d:/item/ProSourcing/auth.json"
        
        context_args = {}
        if os.path.exists(storage_state_path):
            context_args['storage_state'] = storage_state_path
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        # Check login state
        try:
            await page.goto("https://app.algatop.kz/niche", wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Initial navigation to /niche timed out or failed: {e}. Will proceed anyway.")
        
        # 只取前 10 个测试
        for p_data in products[:10]:
            sku = p_data.get("sku")
            if sku:
                enriched = await enrich_product(page, sku)
                p_data.update(enriched)

                
        # Save enriched data
        output_file = "d:/item/ProSourcing/output/enriched_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
            
        print(f"Saved enriched results to {output_file}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(enrich_all())
