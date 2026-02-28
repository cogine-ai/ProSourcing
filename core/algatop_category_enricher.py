import asyncio
import json
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright

async def enrich_product(page, p_data):
    sku = p_data.get("sku")
    if not sku:
        return None
        
    url = f"https://app.algatop.kz/niche/product/{sku}"
    print(f"\n--- Checking SKU {sku} ---")
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(4)
        
        text = await page.inner_text("body", timeout=5000)
        
        # 1. 检查上架时间 (Появилось в Каспи) -> 格式可能是 02.02.2025
        listing_date_str = "N/A"
        days_since_listing = 0
        
        match = re.search(r"Появилось в Каспи\s*(\d{2}\.\d{2}\.\d{4})", text)
        if match:
            listing_date_str = match.group(1)
            date_obj = datetime.strptime(listing_date_str, "%d.%m.%Y")
            days_since_listing = (datetime.now() - date_obj).days
            print(f"[{sku}] Listing Date: {listing_date_str}, Days: {days_since_listing}")
            
            if days_since_listing > 300:
                print(f"[{sku}] FILTERED OUT (Listed {days_since_listing} days ago, > 300)")
                return None
        else:
            print(f"[{sku}] Could not find listing date. Proceeding anyway.")
            
        # 尝试提取单品月销量 "Продажи 2536 шт."
        product_sales = 0
        sales_matches = re.findall(r"Продажи[\s\n]*([\d\s]+)шт", text)
        if sales_matches:
            # 第一张图片里的 "Продажи" 对应商品销量
            product_sales = int(re.sub(r"\s+", "", sales_matches[0]))
            print(f"[{sku}] Product Sales: {product_sales}")
        p_data["sales"] = product_sales
        
        # 提取卖家数 (продавцов)
        sellers_matches = re.findall(r"(\d+)\s*продавцов", text)
        if sellers_matches:
            p_data["sellers"] = int(sellers_matches[0])
            
        # 2. 找到该产品所属的细分类目 URL
        # 根据图2，顶部的面包屑导航是 a 标签。取最后一个带 /niche/category/ 的
        cat_links = await page.locator('a[href*="/niche/category/"]').all()
        if not cat_links:
            print(f"[{sku}] Could not find category link. Skipping.")
            return None
            
        cat_href = await cat_links[-1].get_attribute("href")
        cat_url = f"https://app.algatop.kz{cat_href}" if cat_href.startswith("/") else cat_href
        print(f"[{sku}] Navigating to category: {cat_url}")
        
        # 3. 访问细分类目页
        await page.goto(cat_url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(5)
        
        cat_text = await page.inner_text("body", timeout=5000)
        
        # 提取类目总销量 (Продажи) 和 类目产品总数 (Товары)
        category_sales = 0
        category_products = 0
        
        # 找 'Продажи XX шт.'
        # 根据图2，有大的卡片显示 "Продажи\n 14 715 шт."
        sales_match = re.search(r"Продажи\s*([\d\s]+)шт", cat_text)
        if sales_match:
            category_sales = int(re.sub(r"\s+", "", sales_match.group(1)))
            
        products_match = re.search(r"Товары\s*([\d\s]+)шт", cat_text)
        if products_match:
            category_products = int(re.sub(r"\s+", "", products_match.group(1)))
            
        print(f"[{sku}] Category Sales: {category_sales}, Products: {category_products}")
        
        # 4. 计算 CR3 (前三名销量之和 / 类目销量)
        # 表格里的列包含: Название, Бренд, Продажи, Выручка, Цена, Отзывы ...
        # 我们抓取表格所有的数字行，寻找最前面代表销量的列
        # 最简单粗暴的方法是：提取表格所有的行 (tr)，然后找出销量。
        
        cr3_value = "N/A"
        try:
            # 找到包含商品列表的表格行
            rows = await page.locator("table tr, tbody tr, .rt-tr-group").all()
            sales_list = []
            
            # 判断逻辑：如果我们不能精准点击排序，我们可以抓取当前页所有行的销量并自己排序（通常第一页就是头部商品）
            # 或者通过执行 JS 来找特定的排序按钮并点击
            sort_btn = page.locator("button", has_text="Сортировка:")
            if await sort_btn.count() > 0:
                current_sort = await sort_btn.first.inner_text()
                if "продажам" not in current_sort.lower():
                    print(f"[{sku}] Clicking sort to sales...")
                    # 假定点击后会出现下拉框并选择 'По продажам' 或者点击切换
                    await sort_btn.first.click()
                    await asyncio.sleep(1)
                    # 尝试点击下拉选项
                    sales_option = page.locator("text=По продажам").first
                    if await sales_option.count() > 0:
                        await sales_option.click()
                        await asyncio.sleep(4)
                    else:
                        print(f"[{sku}] Sort option not found. Will just parse current items.")
            
            # 由于 DOM 结构可能很复杂，我们直接取出页面上所有的销量数字。对于表格中的列，我们可以用比较暴力的 JS：
            # 找到带有 "Продажи" 的表头，然后获取对应的列。
            # 这里保守起见，抓取页面上的 HTML 解析
            html = await page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            # 尝试猜测表格结构。通常有一个 div/table 包含多行，每行包含类名带 'sales' 的，或者直接数值
            # 或者暴力：利用正则找 `Артикул: XXXXX` 附近的销量
            # 页面里商品会有 `Артикул: \d+` 然后跟品牌，销量，收入
            
            # 执行 JS 提取所有可能的整行文本，然后根据结构解析
            row_texts = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('div[role="row"], tr')).map(e => e.innerText);
            }''')
            
            parsed_sales = []
            for rt in row_texts:
                if "Артикул" in rt:
                    # 典型的文本块可能长这样：
                    # Коврик для йоги...\nАртикул: 12345\nБез бренда\n10 547\n24 375 330 ₸...
                    # 我们可以通过分行来解析
                    lines = [ln.strip() for ln in rt.split('\n') if ln.strip()]
                    # 寻找纯数字的行（没有 ₸ 的大数字通常是销量）
                    for i, ln in enumerate(lines):
                        if ln.replace(' ', '').isdigit():
                            parsed_sales.append(int(ln.replace(' ', '')))
                            break # 取第一个遇到的纯数字作为销量
                            
            if parsed_sales:
                parsed_sales.sort(reverse=True)
                top_3_sum = sum(parsed_sales[:3])
                if category_sales > 0:
                    cr3_value = f"{(top_3_sum / category_sales * 100):.2f}%"
                print(f"[{sku}] Found {len(parsed_sales)} items in table. Top 3 sum: {top_3_sum}. CR3: {cr3_value}")
        
        except Exception as e:
            print(f"[{sku}] Error calculating CR3: {e}")
            
        
        p_data["listing_date"] = listing_date_str
        p_data["days_since_listing"] = days_since_listing
        p_data["category_sales"] = category_sales
        p_data["category_products"] = category_products
        p_data["cr3"] = cr3_value
        
        # 由于我们进入了 Algatop，也许能更新真实的月销
        # Algatop 上单品的月销（见图1）：我们在第一步能拿到
        # 但是已经跳出了页面。如果需要，应该在第一步提取。
        # 回去稍微写点提取图1的销量：
        # 我们可以在访问 cat_url 之前提取。
        
        return p_data
        
    except Exception as e:
        print(f"[{sku}] General Error: {e}")
        return p_data

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
        
        valid_products = []
        
        for p_data in products:
            if len(valid_products) >= 10:
                print("Collected 10 valid products. Stopping.")
                break
                
            enriched_p = await enrich_product(page, p_data)
            if enriched_p is not None:
                valid_products.append(enriched_p)
                
        # Save enriched data
        output_file = "d:/item/ProSourcing/output/enriched_results_v3.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(valid_products, f, ensure_ascii=False, indent=2)
            
        print(f"Saved {len(valid_products)} enriched results to {output_file}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(enrich_all())
