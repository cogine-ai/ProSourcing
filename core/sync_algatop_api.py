import asyncio
import json
import os
import re
import sys
import io
import datetime
from playwright.async_api import async_playwright

async def sync_algatop_api():
    """
    通过 API 递归获取 Algatop 全量类目树。
    """
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("\n" + "="*60)
    print("🚀 Algatop 全量类目同步工具 (API 递归版 v2)")
    print("="*60)
    
    end_date = datetime.date.today().strftime("%Y%m%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y%m%d")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        
        if not os.path.exists(storage_state):
            print("❌ 错误：检测不到 auth.json")
            await browser.close()
            return

        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        
        # 【关键修复】：先跳转到目标域名，否则 fetch 会因为同源策略报错
        print("🔗 正在建立连接...")
        await page.goto("https://app.algatop.kz/niche", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        category_mapping = {}
        processed_ids = set()
        queue = asyncio.Queue()
        
        # 初始种子
        await queue.put("") 
        
        print(f"📅 日期: {start_date} - {end_date}")

        try:
            while not queue.empty():
                current_id = await queue.get()
                if current_id in processed_ids and current_id != "":
                    continue
                
                processed_ids.add(current_id)
                api_url = f"/api/v1/niche/categoryListStatistic?startDate={start_date}&endDate={end_date}"
                if current_id:
                    api_url += f"&categoryId={current_id}"
                
                # print(f"  📡 请求 ID: {current_id if current_id else 'ROOT'}")
                
                try:
                    # 使用相对路径 fetch，自动复用当前页面的 Cookie
                    response_data = await page.evaluate(f'''async () => {{
                        const res = await fetch("{api_url}");
                        return res.ok ? await res.json() : null;
                    }}''')
                    
                    if not response_data or "data" not in response_data:
                        continue
                    
                    items = response_data["data"]
                    added_this_round = 0
                    for item in items:
                        name = item.get("categoryName", "").strip()
                        cat_id = item.get("categoryId", "")
                        
                        if name and cat_id:
                            # 存储映射
                            category_mapping[name] = cat_id
                            
                            # 如果这个 ID 还没处理过，就进队递归
                            if cat_id not in processed_ids:
                                await queue.put(cat_id)
                                added_this_round += 1
                                
                    print(f"  ✅ 处理 ID: {current_id if current_id else 'ROOT'} | 发现新子类: {added_this_round} | 当前总数: {len(category_mapping)}")
                    
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    print(f"\n⚠️ 接口报错 {current_id}: {e}")
                    continue

            # 保存
            output_path = "d:/item/ProSourcing/output/algatop_id_mapping.json"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(category_mapping, f, ensure_ascii=False, indent=2)
            
            print(f"\n✨ 同步完成！共捕获 {len(category_mapping)} 个 ID。数据已存入 output。")

        except Exception as e:
            print(f"\n❌ 执行故障: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(sync_algatop_api())
