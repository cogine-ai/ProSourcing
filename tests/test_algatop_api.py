import asyncio
import json
import os
import requests
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

def test_algatop_api():
    # 模拟请求马桶刷 SKU
    sku = "113455666"
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
    
    url = f"https://app.algatop.kz/api/v1/niche/product/statistic?code={sku}&startDate={start_date}&endDate={end_date}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://app.algatop.kz/niche/product/{sku}",
        "Cookie": get_auth_cookies(),
        "top-l": "2s3dfnfRgn43PkgmPolqre#"  # 这是我刚抓到的特征 Header
    }
    
    print(f"Testing URL: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("\n[SUCCESS] API Response:")
        # 验证关键字段
        stats_list = data.get("data", {}).get("statistic", [])
        if stats_list:
            stats = stats_list[0]
            print(f"SKU: {stats.get('product_ext_id')}")
            print(f"90-day Sales (sale_qty): {stats.get('sale_qty')}")
            print(f"90-day Revenue (sale_amount): {stats.get('sale_amount')}")
            print(f"Average Merchant Count: {stats.get('merchant_count')}")
        else:
            print("No statistic data found in response.")
    else:
        print(f"\n[FAILED] Status Code: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_algatop_api()
