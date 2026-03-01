import asyncio
import json
import os
import re
import httpx
from datetime import datetime, timedelta
from supabase import create_client, Client

# ==========================================
# 核心配置与初始化
# ==========================================
SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 抓取特征 (来自 Network 拦截)
TOP_L_HEADER = "2s3dfnfRgn43PkgmPolqre#"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_auth_cookies():
    """从本地 auth.json 提取登录 Cookie"""
    cookie_str = ""
    auth_path = "d:/item/ProSourcing/auth.json"
    if os.path.exists(auth_path):
        with open(auth_path, "r") as f:
            state = json.load(f)
            cookies = state.get("cookies", [])
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    return cookie_str

# ==========================================
# 核心 API 请求封装
# ==========================================
async def api_request(client, url, referer, method="GET", json_payload=None):
    headers = {
        "User-Agent": UA,
        "Referer": referer,
        "Cookie": get_auth_cookies(),
        "top-l": TOP_L_HEADER,
        "Content-Type": "application/json",
        "Origin": "https://app.algatop.kz" if "algatop" in url else "https://kaspi.kz"
    }
    try:
        if method == "POST":
            resp = await client.post(url, headers=headers, json=json_payload, timeout=20.0)
        else:
            resp = await client.get(url, headers=headers, timeout=20.0)
            
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        print(f"  [API ERROR] {url}: {e}")
        return None

# ==========================================
# 数据采集主核心 (100% 接口驱动)
# ==========================================
async def enrich_and_insert(client, p_data):
    sku = p_data.get("sku")
    if not sku: return
    
    print(f"\n>>> 正在处理 SKU {sku} <<<")
    
    # 构造 3 个月日期窗口
    today = datetime.now()
    start_date = (today - timedelta(days=90)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    
    # 初始化入库 Payload
    sb_payload = {
        "sku": str(sku),
        "product_name": p_data.get("title", ""),
        "product_url": "https://kaspi.kz" + p_data.get("url", "") if not p_data.get("url", "").startswith("http") else p_data.get("url"),
        "price": float(re.sub(r'[^\d.]', '', str(p_data.get("price", "0")).replace(' ', '')) or 0),
        "reviews_count": int(p_data.get("reviews", 0)),
        "image_url": p_data.get("image_url"),
        "sales_3m": 0, "revenue_3m": 0, "sellers": 0, "rating": 0,
        "category_total_sales": 0, "category_total_products": 0, "top3_sales_sum": 0,
        "brand": None, "listing_date": None, "category_tree": None
    }

    # 1. Algatop 详情 API (取品牌、上架时间、类目 ID)
    detail_url = f"https://app.algatop.kz/api/v1/niche/product/{sku}"
    res_det = await api_request(client, detail_url, f"https://app.algatop.kz/niche/product/{sku}")
    cat_code = None
    if res_det and res_det.get("success"):
        raw_node = res_det.get("data")
        node = raw_node[0] if isinstance(raw_node, list) and raw_node else (raw_node if isinstance(raw_node, dict) else {})
        sb_payload["brand"] = node.get("brand_name")
        sb_payload["listing_date"] = node.get("create_date")
        sb_payload["category_tree"] = node.get("category_name")
        cat_code = node.get("category_code") or node.get("category_ext_id")
        print(f"  [Detail] 品牌: {sb_payload['brand']}, 上架: {sb_payload['listing_date']}")

    # 2. Algatop 统计 API (取 90 天销量/金额)
    stat_url = f"https://app.algatop.kz/api/v1/niche/product/statistic?code={sku}&startDate={start_date}&endDate={end_date}"
    res_stat = await api_request(client, stat_url, f"https://app.algatop.kz/niche/product/{sku}")
    if res_stat and res_stat.get("success"):
        stat_list = res_stat.get("data", {}).get("statistic", [])
        if stat_list:
            s = stat_list[0]
            sb_payload["sales_3m"] = int(s.get("sale_qty") or 0)
            sb_payload["revenue_3m"] = float(s.get("sale_amount") or 0)
            sb_payload["sellers"] = int(s.get("merchant_count") or 0) # API 给出的平均卖家数最准
            print(f"  [Stats] 90天销量: {sb_payload['sales_3m']}, 卖家数: {sb_payload['sellers']}")

    # 3. Kaspi 实时价格与卖家数 (对冲验证)
    kaspi_offers_url = f"https://kaspi.kz/yml/offer-view/offers/{sku}"
    res_kaspi = await api_request(client, kaspi_offers_url, f"https://kaspi.kz/shop/p/-{sku}/", method="POST", json_payload={"cityId": "750000000"})
    if res_kaspi:
        real_sellers = res_kaspi.get("total", 0)
        # 如果实时卖家数更多，更新它
        if real_sellers > sb_payload["sellers"]: sb_payload["sellers"] = real_sellers
        if res_kaspi.get("offers") and len(res_kaspi["offers"]) > 0:
            sb_payload["price"] = float(res_kaspi["offers"][0].get("price") or sb_payload["price"])
        print(f"  [Kaspi] 实时低价: {sb_payload['price']}, 卖家总数: {real_sellers}")

    # 4. 类目概况与 CR3 计算
    if cat_code:
        # 类目 90 天总量
        cat_stat_url = f"https://app.algatop.kz/api/v1/niche/categoryStatistic?categoryCode={cat_code}&startDate={start_date}&endDate={end_date}"
        res_cat = await api_request(client, cat_stat_url, f"https://app.algatop.kz/niche/category/{cat_code}")
        if res_cat and res_cat.get("success"):
            c = res_cat.get("data", {})
            sb_payload["category_total_sales"] = int(c.get("sale_qty") or 0)
            sb_payload["category_total_products"] = int(c.get("sale_product_qty") or 0)
            print(f"  [Category] 总销: {sb_payload['category_total_sales']}, 商品数: {sb_payload['category_total_products']}")

        # 品牌份额计算 CR3
        share_url = f"https://app.algatop.kz/api/v1/niche/categoryStatisticBrandsLine?categoryCode={cat_code}&startDate={start_date}&endDate={end_date}"
        res_share = await api_request(client, share_url, f"https://app.algatop.kz/niche/category/{cat_code}")
        if res_share and res_share.get("success"):
            shares = res_share.get("data", [])
            top3_sum = sum([float(b.get('sale_amount') or 0) for b in shares[:3]])
            total_sum = sum([float(b.get('sale_amount') or 0) for b in shares])
            sb_payload["top3_sales_sum"] = int(top3_sum) # 类目总销售额前三品牌之和
            if total_sum > 0:
                print(f"  [CR3] 类目总额前三和: {int(top3_sum)}, 集中度: {(top3_sum/total_sum*100):.1f}%")

    # 写入 Supabase
    try:
        supabase.table("products_raw_data").upsert(sb_payload).execute()
        print(f"  ✅ [SUCCESS] SKU {sku} 入库成功")
    except Exception as e:
        print(f"  ❌ [DB ERROR] {sku}: {e}")

# ==========================================
# 流程入口
# ==========================================
async def main():
    input_file = "d:/item/ProSourcing/output/kaspi_results.json"
    if not os.path.exists(input_file):
        print(f"错误: 找不到输入文件 {input_file}")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        products = json.load(f)
    print(f"加载马桶刷缓存数据: {len(products)} 条")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        # 并发量限制，防止被封
        semaphore = asyncio.Semaphore(1) 
        async def sem_task(p):
            async with semaphore:
                await enrich_and_insert(client, p)
                await asyncio.sleep(1.5) # 稳一点

        tasks = [sem_task(p) for p in products]
        await asyncio.gather(*tasks)

    print("\n流水线作业完成！请前往 Supabase 查看结果。")

if __name__ == "__main__":
    asyncio.run(main())
