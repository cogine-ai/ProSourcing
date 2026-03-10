import asyncio
import json
import os
import io
import sys
import datetime
from playwright.async_api import async_playwright

async def sync_via_cdp():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("\n" + "="*60)
    print("🚀 Algatop 全量类目同步 (CDP 接管终端版)")
    print("="*60)
    print("💡 方案：连接到您本地 9222 端口的浏览器，借用合法会话同步 ID")

    port = 9222
    end_date = datetime.date.today().strftime("%Y%m%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y%m%d")
    
    async with async_playwright() as p:
        try:
            print(f"🔗 正在连接到本地 Chrome (端口: {port})...")
            # 连接到用户已经打开的浏览器
            browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            context = browser.contexts[0]
            # 创建一个新标签页用于抓取
            page = await context.new_page()
            
            # 必须先跳转到域名下，否则 fetch 会报跨域错误
            await page.goto("https://app.algatop.kz/niche", wait_until="commit")
            await asyncio.sleep(3)

            results = {}
            processed_ids = set()
            queue = asyncio.Queue()
            
            # 种子 ID
            seeds = [""] # 从根开始
            for s in seeds: await queue.put(s)

            print(f"📅 同步周期: {start_date} - {end_date}")
            print("⏳ 正在递归爬取所有层级 (约 2961 个类目)...")

            batch_count = 0
            output_path = "d:/item/ProSourcing/output/algatop_id_mapping.json"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            while not queue.empty():
                current_id = await queue.get()
                if current_id in processed_ids: continue
                processed_ids.add(current_id)

                api_url = f"/api/v1/niche/categoryListStatistic?startDate={start_date}&endDate={end_date}&categoryId={current_id}"
                
                try:
                    # 注入关键 Header
                    data = await page.evaluate(f'''async () => {{
                        const res = await fetch("{api_url}", {{
                            headers: {{ "top-l": "2s3dfnfRgn43PkgmPolqre#" }}
                        }});
                        return res.ok ? await res.json() : null;
                    }}''')

                    if data and data.get("success"):
                        items = data.get("data", [])
                        for item in items:
                            name = item.get("category_name") or item.get("categoryName")
                            cid = item.get("category_id") or item.get("categoryId")
                            if name and cid:
                                results[name] = cid
                                if cid not in processed_ids:
                                    await queue.put(cid)
                    
                    batch_count += 1
                    if batch_count % 10 == 0:
                        print(f"  ✅ 已扫描 {batch_count} 个节点，当前映射总数: {len(results)}")
                        # 实时保存，防止中断
                        with open(output_path, "w", encoding="utf-8") as f:
                            json.dump(results, f, ensure_ascii=False, indent=2)
                    
                    # 极短延迟
                    await asyncio.sleep(0.05)

                except Exception:
                    continue

            # 最终保存
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            print("\n" + "#"*60)
            print(f"🎉 同步大功告成！")
            print(f"🔢 最终同步类目总数: {len(results)}")
            print(f"💾 映射文件路径: {output_path}")
            print("#"*60)

            await browser.close()

        except Exception as e:
            print(f"❌ 连接浏览器或流程失败: {e}")

if __name__ == "__main__":
    asyncio.run(sync_via_cdp())
