import asyncio
import json
import os
import httpx
from datetime import datetime, timedelta

# 从 auth.json 提取 Cookie
def get_auth_cookies():
    cookie_str = ""
    if os.path.exists("d:/item/ProSourcing/auth.json"):
        with open("d:/item/ProSourcing/auth.json", "r") as f:
            state = json.load(f)
            cookies = state.get("cookies", [])
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    return cookie_str

# 核心 Headers
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": UA,
    "top-l": "2s3dfnfRgn43PkgmPolqre#",
    "Cookie": get_auth_cookies()
}

async def test_full_api_coverage():
    sku = "113455666" # 马桶刷
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=90)
    end_str = end_dt.strftime("%Y%m%d")
    start_str = start_dt.strftime("%Y%m%d")

    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"\n--- Testing Algatop Product Detail API ---")
        detail_url = f"https://app.algatop.kz/api/v1/niche/product/{sku}"
        resp_detail = await client.get(detail_url, headers=HEADERS)
        if resp_detail.status_code == 200:
            raw_data = resp_detail.json().get("data", {})
            d = raw_data[0] if isinstance(raw_data, list) and raw_data else (raw_data if isinstance(raw_data, dict) else {})
            print(f"[SUCCESS] Product Detail Found.")
            print(f"  Name: {d.get('product_name')}")
            print(f"  Brand: {d.get('brand_name')}")
            print(f"  Created: {d.get('create_date')}")
            print(f"  Sellers: {d.get('merchant_count')}")
            # 打印全部 key 看看哪个是 Class ID
            print(f"  Available keys: {list(d.keys())}")
            cat_code = d.get('category_code') or d.get('category_ext_id') or d.get('p_category_code')
            print(f"  Detected CatCode: {cat_code}")
            if not cat_code:
                print(f"  Raw JSON for debugging: {json.dumps(d, indent=2, ensure_ascii=False)}")
        else:
            print(f"[FAILED] Detail API: {resp_detail.status_code}")

        print(f"\n--- Testing Algatop Brand Market Share (for CR3) ---")
        if cat_code:
            # 品牌份额接口
            share_url = f"https://app.algatop.kz/api/v1/niche/categoryStatisticBrandsLine?categoryCode={cat_code}&startDate={start_str}&endDate={end_str}"
            resp_share = await client.get(share_url, headers=HEADERS)
            if resp_share.status_code == 200:
                shares = resp_share.json().get("data", [])
                print(f"[SUCCESS] Brand Shares Found: {len(shares)} brands.")
                # 这里可以计算 CR3: 前三名销售额 / 总销售额
                if shares:
                    top3_sum = sum([float(b.get('sale_amount') or 0) for b in shares[:3]])
                    total_sum = sum([float(b.get('sale_amount') or 0) for b in shares])
                    cr3 = (top3_sum / total_sum * 100) if total_sum > 0 else 0
                    print(f"  Calculated CR3: {cr3:.2f}%")
            else:
                print(f"[FAILED] Share API: {resp_share.status_code} - {resp_share.text}")
        else:
            print("[SKIP] CatCode not found, skipping Share API.")

        print(f"\n--- Testing Kaspi Offers API ---")
        kaspi_url = f"https://kaspi.kz/yml/offer-view/offers/{sku}"
        kaspi_headers = {
            "User-Agent": UA,
            "Referer": f"https://kaspi.kz/shop/p/-{sku}/",
            "Content-Type": "application/json",
            "Origin": "https://kaspi.kz"
        }
        resp_kaspi = await client.post(kaspi_url, json={"cityId": "750000000"}, headers=kaspi_headers)
        if resp_kaspi.status_code == 200:
            k_data = resp_kaspi.json()
            print(f"[SUCCESS] Kaspi Offers Found.")
            print(f"  Total Merchants: {k_data.get('total')}")
            if k_data.get('offers'):
                print(f"  Lowest Price: {k_data['offers'][0].get('price')} ₸")
        else:
            print(f"[FAILED] Kaspi API: {resp_kaspi.status_code}")

if __name__ == "__main__":
    asyncio.run(test_full_api_coverage())
