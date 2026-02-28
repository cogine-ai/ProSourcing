import asyncio
import json
import os
import re
import httpx
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from supabase import create_client, Client

# Supabase init
SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 抓取配置 (Header 来自 Network 拦截结果)
TOP_L_HEADER = "2s3dfnfRgn43PkgmPolqre#"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_auth_cookies():
    cookie_str = ""
    if os.path.exists("d:/item/ProSourcing/auth.json"):
        with open("d:/item/ProSourcing/auth.json", "r") as f:
            state = json.load(f)
            cookies = state.get("cookies", [])
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    return cookie_str

async def fetch_api(client, url, referer):
    headers = {
        "User-Agent": UA,
        "Referer": referer,
        "Cookie": get_auth_cookies(),
        "top-l": TOP_L_HEADER
    }
    try:
        response = await client.get(url, headers=headers, timeout=30.0)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  [API ERR] {url} -> {response.status_code}")
            return None
    except Exception as e:
        print(f"  [API EXC] {url} -> {e}")
        return None

async def enrich_and_insert(client, p_data):
    sku = p_data.get("sku")
    if not sku: return None
    
    print(f"\n--- Processing SKU {sku} ---")
    
    # 构造 90 天日期范围
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=90)
    end_str = end_dt.strftime("%Y%m%d")
    start_str = start_dt.strftime("%Y%m%d")
    
    # Payload 初始化
    sb_payload = {
        "sku": str(sku),
        "product_name": p_data.get("title", ""),
        "product_url": "https://kaspi.kz" + p_data.get("url", "") if not p_data.get("url", "").startswith("http") else p_data.get("url"),
        "price": float(re.sub(r'[^\d.]', '', str(p_data.get("price", "0")).replace(' ', '')) or 0),
        "reviews_count": int(p_data.get("reviews", 0)),
        "image_url": p_data.get("image_url"),
        "sellers": 0, "sales_3m": 0, "revenue_3m": 0,
        "category_total_sales": 0, "category_total_products": 0, "top3_sales_sum": 0
    }

    # 1. 获取单品 90 天统计数据
    stats_url = f"https://app.algatop.kz/api/v1/niche/product/statistic?code={sku}&startDate={start_str}&endDate={end_str}"
    res_stats = await fetch_api(client, stats_url, f"https://app.algatop.kz/niche/product/{sku}")
    
    if res_stats and res_stats.get("success"):
        stats_list = res_stats.get("data", {}).get("statistic", [])
        if stats_list:
            s = stats_list[0]
            sb_payload["sales_3m"] = int(s.get("sale_qty") or 0)
            sb_payload["revenue_3m"] = float(s.get("sale_amount") or 0)
            sb_payload["sellers"] = int(s.get("merchant_count") or 0)
            sb_payload["rating"] = float(s.get("product_rate") or 0)
            print(f"  [API] Sales: {sb_payload['sales_3m']}, Sellers: {sb_payload['sellers']}")

    # 2. 基础属性 Fallback：如果 API 没给到位，我们用 Playwright 详情页解析
    detail_url = f"https://app.algatop.kz/api/v1/niche/product/detail?code={sku}"
    res_detail = await fetch_api(client, detail_url, f"https://app.algatop.kz/niche/product/{sku}")
    
    cat_code = None
    if res_detail and res_detail.get("success"):
        data_node = res_detail.get("data")
        d = data_node[0] if isinstance(data_node, list) and data_node else (data_node if isinstance(data_node, dict) else {})
        sb_payload["brand"] = d.get("brand_name")
        sb_payload["listing_date"] = d.get("p_created_at")
        sb_payload["category_tree"] = d.get("category_name")
        cat_code = d.get("category_code")

    # 如果 API 没给品牌或日期，我们从 Page 文本里抠
    if not sb_payload["brand"] or not sb_payload["listing_date"]:
        try:
            await page.goto(f"https://app.algatop.kz/niche/product/{sku}", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)
            p_text = await page.inner_text("body")
            p_lines = [l.strip() for l in p_text.split('\n') if l.strip()]
            
            # 从页面文本 Fallback
            def get_next(ks, key):
                for i, ln in enumerate(ks):
                    if key in ln and i+1 < len(ks): return ks[i+1]
                return None
            
            if not sb_payload["brand"]: 
                sb_payload["brand"] = get_next(p_lines, "Бренд")
            if not sb_payload["listing_date"]:
                raw_date = get_next(p_lines, "Появилось в Каспи")
                if raw_date and re.match(r'\d{2}\.\d{2}\.\d{4}', raw_date):
                    sb_payload["listing_date"] = datetime.strptime(raw_date[:10], "%d.%m.%Y").strftime("%Y-%m-%d")
            
            # 如果接口没给类目 ID，我们从详情页链接里抠最后一个
            if not cat_code:
                cat_link_el = page.locator('a[href*="/niche/category/"]').last
                if await cat_link_el.count() > 0:
                    href = await cat_link_el.get_attribute("href")
                    # /niche/category/00002 -> 00002
                    cat_code = href.split('/')[-1]
                    if not sb_payload["category_tree"]:
                        sb_payload["category_tree"] = (await cat_link_el.inner_text()).strip()
        except: pass

    # 3. 获取类目汇总数据 (90天)
    if cat_code:
        cat_url = f"https://app.algatop.kz/api/v1/niche/categoryStatistic?categoryCode={cat_code}&startDate={start_str}&endDate={end_str}"
        res_cat = await fetch_api(client, cat_url, f"https://app.algatop.kz/niche/category/{cat_code}")
        if res_cat and res_cat.get("success"):
            c = res_cat.get("data", {})
            sb_payload["category_total_sales"] = int(c.get("sale_qty") or 0)
            sb_payload["category_total_products"] = int(c.get("sale_product_qty") or 0)
            print(f"  [API] Cat Sales: {sb_payload['category_total_sales']}, Cat Products: {sb_payload['category_total_products']}")

        # 4. 获取 CR3
        list_url = f"https://app.algatop.kz/api/v1/niche/categoryListStatistic?categoryCode={cat_code}&startDate={start_str}&endDate={end_str}&offset=0&limit=10&sortField=sale_qty&sortOrder=desc"
        res_list = await fetch_api(client, list_url, f"https://app.algatop.kz/niche/category/{cat_code}")
        if res_list and res_list.get("success"):
            items = res_list.get("data", {}).get("list", [])
            top3_sum = sum([int(i.get("sale_qty") or 0) for i in items[:3]])
            sb_payload["top3_sales_sum"] = top3_sum
            print(f"  [API] Top3 Sales Sum: {top3_sum}")

    # Upsert to Supabase
    try:
        supabase.table("products_raw_data").upsert(sb_payload).execute()
        print(f"  [OK] SKU {sku} inserted.")
        return True
    except Exception as e:
        print(f"  [DB ERR] {e}")
        return False

async def run_pipeline():
    with open("d:/item/ProSourcing/output/kaspi_results.json", "r", encoding="utf-8") as f:
        products = json.load(f)
    print(f"Loaded {len(products)} products from Kaspi cache.")

    async with httpx.AsyncClient() as client:
        success_count = 0
        for p_data in products:
            if await enrich_and_insert(client, p_data):
                success_count += 1
            await asyncio.sleep(1) # 礼貌抓取
            
    print(f"\nDone! {success_count}/{len(products)} products processed via API.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
