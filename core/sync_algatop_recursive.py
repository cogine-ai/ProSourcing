import asyncio
import json
import os
import sys
import io
import datetime
from playwright.async_api import async_playwright

async def sync_recursive():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("\n" + "="*60)
    print("🚀 Algatop 全量类目同步工具 (API 递归终极版 v4)")
    print("="*60)
    print("💡 已注入关键 Header: top-l")
    print("💡 已匹配字段名: category_id, category_name")

    # 根据 Subagent 获取到的准确种子开展
    seeds = [
        "00754", "00791", "00864", "00933", "01466", "01793", "02062", "02605", 
        "02807", "06498", "00001", "00002", "00003", "00004", "00005", "00006"
    ]
    
    # 也可以加上用户提到的一系列 ID
    extra_seeds = [f"{i:05d}" for i in range(1, 25)]
    all_seeds = list(set(seeds + extra_seeds))
    
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
        
        print("🔗 正在建立连接...")
        try:
            await page.goto("https://app.algatop.kz/niche", wait_until="commit", timeout=60000)
        except:
            print("  ⚠️ 页面加载较慢，但不影响接口调用...")

        category_mapping = {}
        processed_ids = set()
        queue = asyncio.Queue()
        
        for s in all_seeds:
            await queue.put(s)
            
        print(f"📅 日期范围: {start_date} - {end_date}")
        print(f"🔍 初始种子数: {len(all_seeds)}")

        batch_count = 0
        try:
            while not queue.empty():
                current_id = await queue.get()
                if current_id in processed_ids:
                    continue
                
                processed_ids.add(current_id)
                api_url = f"/api/v1/niche/categoryListStatistic?startDate={start_date}&endDate={end_date}&categoryId={current_id}"
                
                try:
                    response_data = await page.evaluate(f'''async () => {{
                        try {{
                            const res = await fetch("{api_url}", {{
                                headers: {{
                                    "top-l": "2s3dfnfRgn43PkgmPolqre#",
                                    "referer": "https://app.algatop.kz/niche"
                                }}
                            }});
                            return res.ok ? await res.json() : null;
                        }} catch (e) {{
                            return null;
                        }}
                    }}''')
                    
                    if not response_data or "data" not in response_data:
                        continue
                    
                    items = response_data["data"]
                    if not items or not isinstance(items, list): continue

                    for item in items:
                        # 重点：Subagent 发现返回的是 category_id 和 category_name (snake_case)
                        name = item.get("category_name") or item.get("categoryName")
                        cat_id = item.get("category_id") or item.get("categoryId")
                        
                        if name and cat_id:
                            name = name.strip()
                            category_mapping[name] = cat_id
                            if cat_id not in processed_ids:
                                await queue.put(cat_id)
                                
                    batch_count += 1
                    if batch_count % 10 == 0:
                        print(f"  ✅ 已抓取节点数: {batch_count}, 发现映射数: {len(category_mapping)}")
                    
                    # 频率控制
                    await asyncio.sleep(0.2)
                    
                except Exception:
                    continue

            # 保存结果
            output_path = "d:/item/ProSourcing/output/algatop_id_mapping.json"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(category_mapping, f, ensure_ascii=False, indent=2)
            
            print("\n" + "#"*60)
            print(f"🎉 递归同步完成！")
            print(f"🔢 最终捕获类目数量: {len(category_mapping)}")
            print(f"💾 结果已存入: {output_path}")
            print("#"*60)

        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(sync_recursive())
