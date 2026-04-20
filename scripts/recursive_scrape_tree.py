import asyncio
import json
import os
from playwright.async_api import async_playwright

async def recursive_scrape():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = context.pages[0] # 假设第一个页面就是
        
        all_nodes = []
        visited_ids = set()
        
        # 基础 API 地址 (哥，我发现只要带上基本的日期参数就行)
        base_url = "https://app.algatop.kz/api/v1/niche/categoryListStatistic?startDate=20260321&endDate=20260420"

        async def fetch_level(parent_id=""):
            nonlocal all_nodes
            
            # 构造请求脚本，在浏览器环境执行以带上所有 Cookie 和 Auth
            url = base_url
            if parent_id:
                url += f"&parentId={parent_id}"
            
            print(f"Fetching: {url}")
            
            script = f'''async () => {{
                try {{
                    const res = await fetch("{url}", {{
                        headers: {{ "accept": "application/json" }}
                    }});
                    return await res.json();
                }} catch (e) {{
                    return {{ success: false, error: e.toString() }};
                }}
            }}'''
            
            result = await page.evaluate(script)
            if not result.get("success"):
                print(f"Error fetching {parent_id}: {result.get('error')}")
                return
            
            lines = result.get("data", [])
            if not isinstance(lines, list):
                # 兼容不同格式
                lines = result.get("data", {}).get("lines", [])
            
            if not lines:
                return

            for item in lines:
                cid = item.get("category_id")
                if cid and cid not in visited_ids:
                    visited_ids.add(cid)
                    all_nodes.append(item)
                    # 如果还有子类，递归抓取
                    if item.get("is_has_subcategory") == 1:
                        # 稍微延迟一下，防止被封
                        await asyncio.sleep(0.5)
                        await fetch_level(cid)

        print("Starting recursive scrape...")
        await fetch_level("") # 从根节点开始
        
        output_path = "scripts/algatop_full_tree_final.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_nodes, f, ensure_ascii=False, indent=2)
            
        print(f"DONE! Total categories scraped: {len(all_nodes)}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(recursive_scrape())
