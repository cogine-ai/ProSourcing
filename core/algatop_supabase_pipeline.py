import asyncio
import json
import os
import re
import random
import httpx
from datetime import datetime, timedelta
from supabase import create_client, Client
from playwright.async_api import async_playwright

# ==========================================
# 核心配置
# ==========================================
SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 动态反爬 Header 与 基础配置
UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

def get_auth_json():
    auth_path = "d:/item/ProSourcing/auth.json"
    if os.path.exists(auth_path):
        with open(auth_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# ==========================================
# 核心采集逻辑 (v2.0 隐身模式)
# ==========================================
class ProSourcingCollector:
    def __init__(self):
        self.browser = None
        self.context = None
        self.auth_data = get_auth_json()

    async def init(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False) # 哥，还是开着看比较稳
        self.context = await self.browser.new_context(
            storage_state=self.auth_data,
            user_agent=random.choice(UA_LIST)
        )

    async def fetch_kaspi_realtime(self, sku):
        """精准获取 Kaspi 最低价和卖家数 (对冲)"""
        url = f"https://kaspi.kz/yml/offer-view/offers/{sku}"
        headers = {
            "User-Agent": random.choice(UA_LIST),
            "Referer": f"https://kaspi.kz/shop/p/-{sku}/",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                # 给阿拉木图 (750000000) 发送请求
                r = await client.post(url, json={"cityId": "750000000"}, headers=headers)
                if r.status_code == 200:
                    data = r.json()
                    offers = data.get("offers", [])
                    total_sellers = data.get("total", 0)
                    min_price = 0
                    if offers:
                        prices = [float(o.get('price') or 9999999) for o in offers]
                        min_price = min(prices)
                    return {"price": min_price, "sellers": total_sellers}
            except Exception as e:
                print(f"  [Kaspi Error] {sku}: {e}")
        return None

    async def scrape_sku_with_stealth(self, p_brief):
        sku = p_brief.get("sku")
        print(f"\n--- 正在隐身采集 SKU: {sku} ---")
        
        # 结果 Payload
        payload = {
            "sku": str(sku),
            "product_name": p_brief.get("title", ""),
            "product_url": "https://kaspi.kz" + p_brief.get("url", "") if "/p/" in p_brief.get("url", "") else p_brief.get("url"),
            "image_url": p_brief.get("image_url"),
            "reviews_count": int(p_brief.get("reviews", 0)),
            "sales_3m": 0, "revenue_3m": 0, "rating": 0, "sellers": 0,
            "brand": None, "listing_date": None, "category_tree": None,
            "category_total_sales": 0, "category_total_products": 0, "top3_sales_sum": 0
        }

        # 1. 优先拿 Kaspi 实时对冲数据 (价格取 min)
        kaspi_data = await self.fetch_kaspi_realtime(sku)
        if kaspi_data:
            payload["price"] = kaspi_data["price"]
            payload["sellers"] = kaspi_data["sellers"]
            print(f"  [Kaspi] 锁定最低价: {payload['price']}, 卖家数: {payload['sellers']}")

        # 2. 模拟真人在 Algatop 截包
        page = await self.context.new_page()
        try:
            # 伪造随机延时
            await asyncio.sleep(random.uniform(1, 3))
            
            # 使用官方 URL，自动利用 Cookie 完成授权
            url = f"https://app.algatop.kz/niche/product/{sku}"
            await page.goto(url, wait_until="domcontentloaded", timeout=40000)
            
            # 零点击日期获取：直接在内核运行 JS 请求统计接口
            # 构造 90 天日期
            today = datetime.now()
            s_date = (today - timedelta(days=90)).strftime("%Y%m%d")
            e_date = today.strftime("%Y%m%d")

            # 拦截数据逻辑 (直接调用 API 并转发)
            js_code = f"""
                async () => {{
                    try {{
                        const detail = await fetch('/api/v1/niche/product/{sku}').then(r => r.json());
                        const stats = await fetch('/api/v1/niche/product/statistic?code={sku}&startDate={s_date}&endDate={e_date}').then(r => r.json());
                        return {{ detail, stats }};
                    }} catch (e) {{ return null; }}
                }}
            """
            api_data = await page.evaluate(js_code)
            
            if api_data:
                # 解析详情
                raw_node = api_data['detail'].get('data')
                node = raw_node[0] if isinstance(raw_node, list) and raw_node else (raw_node if isinstance(raw_node, dict) else {})
                payload["brand"] = node.get("brand_name")
                payload["listing_date"] = node.get("create_date")
                payload["category_tree"] = node.get("category_name")
                cat_code = node.get("category_code") or node.get("category_ext_id")

                # 解析统计 (对齐 90 天)
                s_list = api_data['stats'].get('data', {}).get('statistic', [])
                if s_list:
                    s = s_list[0]
                    payload["sales_3m"] = int(s.get("sale_qty") or 0)
                    payload["revenue_3m"] = float(s.get("sale_amount") or 0)
                    # 如果 API 里的平均卖家数更有参考价值，可以视情况对冲
                    if not payload["sellers"]: payload["sellers"] = int(s.get("merchant_count") or 0)
                
                print(f"  [Algatop] 品牌: {payload['brand']}, 90天销量: {payload['sales_3m']}")

                # 3. 如果拿到了 CatCode，顺手把类目汇总也做了
                if cat_code:
                    js_cat = f"""
                        async () => {{
                            const cat_stat = await fetch('/api/v1/niche/categoryStatistic?categoryCode={cat_code}&startDate={s_date}&endDate={e_date}').then(r => r.json());
                            const cat_share = await fetch('/api/v1/niche/categoryStatisticBrandsLine?categoryCode={cat_code}&startDate={s_date}&endDate={e_date}').then(r => r.json());
                            return {{ cat_stat, cat_share }};
                        }}
                    """
                    cat_data = await page.evaluate(js_cat)
                    if cat_data:
                        cs = cat_data['cat_stat'].get('data', {})
                        payload["category_total_sales"] = int(cs.get("sale_qty") or 0)
                        payload["category_total_products"] = int(cs.get("sale_product_qty") or 0)
                        
                        shares = cat_data['cat_share'].get('data', [])
                        if shares:
                            payload["top3_sales_sum"] = int(sum([float(b.get('sale_amount') or 0) for b in shares[:3]]))

            # 写入 Supabase
            supabase.table("products_raw_data").upsert(payload).execute()
            print(f"  ✅ [SUCCESS] {sku} 入库成功")

        except Exception as e:
            print(f"  ❌ [ERROR] {sku}: {e}")
        finally:
            await page.close()

    async def close(self):
        await self.browser.close()
        await self.playwright.stop()

# ==========================================
# 入口
# ==========================================
async def main():
    input_file = "d:/item/ProSourcing/output/kaspi_results.json"
    with open(input_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    collector = ProSourcingCollector()
    await collector.init()
    
    # 严格限流，模拟真人节奏
    for p in products:
        await collector.scrape_sku_with_stealth(p)
        await asyncio.sleep(random.uniform(5, 10)) # 哥，咱们慢一点，账号要紧

    await collector.close()

if __name__ == "__main__":
    asyncio.run(main())
