import asyncio
import json
import os
import httpx
from datetime import datetime, timedelta

# 从 auth.json 提取 Cookie
def get_auth_cookies():
    cookie_str = ""
    auth_path = "d:/item/ProSourcing/auth.json"
    if os.path.exists(auth_path):
        with open(auth_path, "r") as f:
            state = json.load(f)
            cookies = state.get("cookies", [])
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    return cookie_str

# 核心 Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "top-l": "2s3dfnfRgn43PkgmPolqre#",
    "Cookie": get_auth_cookies()
}

async def diagnose_sku():
    sku = "112769474" # 无人机
    today = datetime.now()
    start_str = (today - timedelta(days=90)).strftime("%Y%m%d")
    end_str = today.strftime("%Y%m%d")

    async with httpx.AsyncClient(timeout=30.0) as client:
        detail_url = f"https://app.algatop.kz/api/v1/niche/product/{sku}"
        resp_detail = await client.get(detail_url, headers=HEADERS)
        if resp_detail.status_code == 200:
            raw_data = resp_detail.json().get("data", {})
            d = raw_data[0] if isinstance(raw_data, list) and raw_data else (raw_data if isinstance(raw_data, dict) else {})
            print(f"\n[Algatop Detail]")
            print(f"  Name: {d.get('product_name')}")
            print(f"  Brand: {d.get('brand_name')}")
            # 查找可能的 cat_code 字段
            cat_fields = {k: v for k, v in d.items() if 'cat' in k.lower() or 'id' in k.lower()}
            print(f"  Category Fields: {cat_fields}")
            cat_code = d.get('category_code') or d.get('category_ext_id') or d.get('p_category_code')
            print(f"  Detected CatCode: {cat_code}")
        
        stat_url = f"https://app.algatop.kz/api/v1/niche/product/statistic?code={sku}&startDate={start_str}&endDate={end_str}"
        resp_stat = await client.get(stat_url, headers=HEADERS)
        if resp_stat.status_code == 200:
            s_data = resp_stat.json().get("data", {})
            stats = s_data.get("statistic", [])
            print(f"\n[Algatop Statistics (Range: {start_str}-{end_str})]")
            if stats:
                s = stats[0]
                print(f"  Sale Qty: {s.get('sale_qty')}")
                print(f"  Sale Amount: {s.get('sale_amount')}")
                print(f"  Merchant Count: {s.get('merchant_count')}")
            else:
                print("  No statistics found.")
        
        kaspi_url = f"https://kaspi.kz/yml/offer-view/offers/{sku}"
        kaspi_headers = {"User-Agent": HEADERS["User-Agent"], "Referer": f"https://kaspi.kz/shop/p/-{sku}/", "Content-Type": "application/json"}
        resp_kaspi = await client.post(kaspi_url, json={"cityId": "750000000"}, headers=kaspi_headers)
        if resp_kaspi.status_code == 200:
            k = resp_kaspi.json()
            offers = k.get("offers", [])
            if offers:
                min_price = min([float(o.get('price') or 9999999) for o in offers])
                print(f"\n[Kaspi Offers]")
                print(f"  Min Price: {min_price}")
                print(f"  Total Sellers: {k.get('total')}")

if __name__ == "__main__":
    asyncio.run(diagnose_sku())
