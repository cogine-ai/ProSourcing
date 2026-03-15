import asyncio
import json
import os
import datetime
from playwright.async_api import async_playwright

async def run_recursive_sync():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print("Failed to connect:", e)
            return
            
        page = None
        for p_obj in browser.contexts[0].pages:
            if "algatop.kz/niche" in p_obj.url:
                page = p_obj
                break
                
        if not page:
            print("Target page not found")
            return
            
        print("Starting Recursive API Tree Extraction (Internal Fetch)...")
        
        today = datetime.date.today().strftime("%Y%m%d")
        last_month = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y%m%d")
        
        # 1. 第一步：获取一级类目 (从 DOM 获取最快最准)
        roots = await page.evaluate('''
            () => {
                const results = [];
                const rows = Array.from(document.querySelectorAll('tr'));
                rows.forEach(r => {
                    const link = r.querySelector('a[href*="/niche/category/"]');
                    if (!link) return;
                    
                    // 只有 padding 为 0 的才是一级 (或者没有 padding)
                    const firstCell = r.querySelector('td, th');
                    let paddingStr = "0rem";
                    if (firstCell && firstCell.firstElementChild) {
                       paddingStr = firstCell.firstElementChild.style.paddingLeft || "0rem";
                    }
                    if (parseFloat(paddingStr) === 0) {
                        const id = link.href.match(/\\/category\\/(\\d+)/)[1];
                        results.push({ id, name: link.innerText.trim() });
                    }
                });
                return results;
            }
        ''')
        
        print(f"Found {len(roots)} root categories.")
        
        all_nodes = {} # id -> node
        queue = []
        for r in roots:
            node = { "id": r['id'], "name": r['name'], "parent_id": None, "children": [], "level": 0 }
            all_nodes[r['id']] = node
            queue.append(r['id'])
            
        # 2. 递归拉取子类目
        js_fetch_children = f'''
        async (catId) => {{
            const url = `/api/v1/niche/categoryListStatistic?startDate={last_month}&endDate={today}&categoryId=${{catId}}`;
            try {{
                const res = await fetch(url, {{
                    headers: {{
                        "top-l": "2s3dfnfRgn43PkgmPolqre#",
                        "Accept": "application/json, text/plain, */*"
                    }}
                }});
                if (!res.ok) return null;
                const json = await res.json();
                return json.data || [];
            }} catch (e) {{
                return null;
            }}
        }}
        '''
        
        processed_count = 0
        while queue:
            current_id = queue.pop(0)
            processed_count += 1
            if processed_count % 20 == 0:
                print(f"  Processed {processed_count} nodes... Queue size: {len(queue)}")
            
            children_data = await page.evaluate(js_fetch_children, current_id)
            if children_data:
                parent_node = all_nodes[current_id]
                for item in children_data:
                    child_id = item.get("category_id")
                    child_name = item.get("category_name")
                    if child_id and child_id not in all_nodes:
                        child_node = {
                            "id": child_id,
                            "name": child_name.strip(),
                            "parent_id": current_id,
                            "children": [],
                            "level": parent_node["level"] + 1
                        }
                        all_nodes[child_id] = child_node
                        parent_node["children"].append(child_node)
                        queue.append(child_id)
            
            # 稍作停顿，避免被封
            await asyncio.sleep(0.1)

        # 3. 组装最终的树
        tree = [node for node in all_nodes.values() if node["parent_id"] is None]
        
        out_path = "d:/item/ProSourcing/output/algatop_full_tree_api.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)
            
        print(f"Total entries found: {len(all_nodes)}")
        print(f"Tree structure saved to {out_path}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_recursive_sync())
