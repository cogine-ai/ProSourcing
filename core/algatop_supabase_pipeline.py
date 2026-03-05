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

    async def scrape_sku_with_stealth(self, p_brief, task_id=None):
        sku = p_brief.get("sku")
        print(f"\n--- 正在隐身全量采集 SKU: {sku} ---")
        
        # 结果 Payload (对齐 V2.0 Schema)
        payload = {
            "sku": str(sku),
            "task_id": task_id,
            "product_name": p_brief.get("title") or p_brief.get("product_name", ""),
            "product_url": "https://kaspi.kz" + p_brief.get("url", "") if p_brief.get("url", "").startswith("/") else p_brief.get("url", ""),
            "sale_price": float(p_brief.get("price") or 0),
            "review_qty": int(p_brief.get("reviews") or 0),
            "sale_qty": 0, 
            "sale_amount": 0, 
            "product_rate": 0, 
            "merchant_count": 0,
            "brand_name": None, 
            "gen_brand_id": None,
            "created_dt": None, 
            "last_sale_date": None,
            "amount_abc": None, 
            "amount_prc": None,
            "preview_image_list": None,
            "category_name": None,
            "category_ext_id": None,
            "restrict_type": None
        }

        # 1. 优先拿 Kaspi 实时对冲数据
        kaspi_data = await self.fetch_kaspi_realtime(sku)
        if kaspi_data:
            payload["sale_price"] = kaspi_data["price"]
            payload["merchant_count"] = kaspi_data["sellers"]
            print(f"  [Kaspi] 实时价格: {payload['sale_price']}, 商家数: {payload['merchant_count']}")

        # 2. 模拟真人在 Algatop 截包
        page = await self.context.new_page()
        try:
            await asyncio.sleep(random.uniform(1, 2))
            url = f"https://app.algatop.kz/niche/product/{sku}"
            await page.goto(url, wait_until="domcontentloaded", timeout=40000)
            
            today = datetime.now()
            s_date = (today - timedelta(days=90)).strftime("%Y%m%d")
            e_date = today.strftime("%Y%m%d")

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
                raw_node = api_data['detail'].get('data')
                node = raw_node[0] if isinstance(raw_node, list) and raw_node else (raw_node if isinstance(raw_node, dict) else {})
                
                # 核心字段映射 (对应 接口 4/5)
                payload["brand_name"] = node.get("brand_name")
                payload["gen_brand_id"] = node.get("gen_brand_id")
                payload["created_dt"] = node.get("create_date")
                payload["last_sale_date"] = node.get("last_sale_date")
                payload["product_rate"] = float(node.get("product_rate") or 0)
                payload["category_name"] = node.get("category_name")
                payload["category_ext_id"] = node.get("category_ext_id")
                payload["restrict_type"] = node.get("restrict_type")
                
                # 图片列表 (JSONB)
                img_list_str = node.get("image_list")
                if img_list_str:
                    try:
                        payload["preview_image_list"] = json.loads(img_list_str) if isinstance(img_list_str, str) else img_list_str
                    except: pass

                # 统计数据映射
                s_list = api_data['stats'].get('data', {}).get('statistic', [])
                if s_list:
                    s = s_list[0]
                    payload["sale_qty"] = int(s.get("sale_qty") or 0)
                    payload["sale_amount"] = float(s.get("sale_amount") or 0)
                    payload["amount_abc"] = s.get("amount_abc")
                    payload["amount_prc"] = float(s.get("amount_prc") or 0)
                    if not payload["merchant_count"]: 
                        payload["merchant_count"] = int(s.get("merchant_count") or 0)
                
                print(f"  [Algatop] 品牌: {payload['brand_name']}, ABC: {payload['amount_abc']}, 销量: {payload['sale_qty']}")

                # 3. 类目大盘回填 (仅首个 SKU 执行或每任务执行一次)
                if task_id:
                    cat_code = node.get("category_ext_id")
                    if cat_code:
                        js_cat = f"""
                            async () => {{
                                try {{
                                    const cat_stat = await fetch('/api/v1/niche/categoryStatistic?categoryCode={cat_code}&startDate={s_date}&endDate={e_date}').then(r => r.json());
                                    const cat_trend = await fetch('/api/v1/niche/categoryStatisticLine?categoryCode={cat_code}&startDate={s_date}&endDate={e_date}').then(r => r.json());
                                    return {{ cat_stat, cat_trend }};
                                }} catch(e) {{ return null; }}
                            }}
                        """
                        cat_res = await page.evaluate(js_cat)
                        if cat_res:
                            # 更新任务表
                            update_task = {
                                "category_id": cat_code,
                                "category_stats": cat_res.get('cat_stat', {}).get('data', {}).get('statistic', [{}])[0],
                                "trend_data": cat_res.get('cat_trend', {}).get('data', []),
                                "up_categories": cat_res.get('cat_stat', {}).get('data', {}).get('up_categories_json')
                            }
                            supabase.table("analysis_tasks").update(update_task).eq("id", task_id).execute()
                            print(f"  [Task Update] 类目大盘与趋势数据回填成功")

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
async def main(category=None, task_id=None, input_file=None):
    if not input_file:
        input_file = "d:/item/ProSourcing/output/kaspi_results.json"
    
    if not os.path.exists(input_file):
        print(f"警告: {input_file} 不存在")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    collector = ProSourcingCollector()
    await collector.init()
    
    # 极其严格限流 (测试模式：前5条)
    for p in products[:5]:
        await collector.scrape_sku_with_stealth(p, task_id=task_id)
        await asyncio.sleep(random.uniform(2, 4)) 

    await collector.close()

if __name__ == "__main__":
    import sys
    cat = sys.argv[1] if len(sys.argv) > 1 else None
    tid = sys.argv[2] if len(sys.argv) > 2 else None
    infile = sys.argv[3] if len(sys.argv) > 3 else None
    asyncio.run(main(cat, tid, infile))
