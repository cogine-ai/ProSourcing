import asyncio
import json
import os
import datetime
import traceback
from playwright.async_api import async_playwright

async def run_recursive_sync_parallel():
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
            
        print("Starting Parallel Recursive API Tree Extraction...")
        
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
        
        print(f"Initial Roots: {len(roots)}")
        
        all_nodes = {} # id -> node
        queue = asyncio.Queue()
        processed_ids = set()
        
        for r in roots:
            node = { "id": r['id'], "name": r['name'], "parent_id": None, "children": [], "level": 0 }
            all_nodes[r['id']] = node
            await queue.put(r['id'])
            
        # 2. 并行抓取逻辑
        CONCURRENCY = 5
        
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
        
        async def worker():
            nonlocal processed_count
            while not queue.empty() or pending_workers > 0:
                try:
                    # 获取下一个 ID
                    try:
                        current_id = await asyncio.wait_for(queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue
                        
                    if current_id in processed_ids:
                        queue.task_done()
                        continue
                    
                    processed_ids.add(current_id)
                    
                    # 抓取子类目
                    children_data = await page.evaluate(js_fetch_children, current_id)
                    
                    if children_data:
                        parent_node = all_nodes[current_id]
                        for item in children_data:
                            child_id = item.get("category_id")
                            child_name = item.get("category_name")
                            if child_id and child_id not in all_nodes:
                                child_node = {
                                    "id": child_id,
                                    "name": (child_name or "Unknown").strip(),
                                    "parent_id": current_id,
                                    "children": [],
                                    "level": parent_node["level"] + 1
                                }
                                all_nodes[child_id] = child_node
                                parent_node["children"].append(child_node)
                                await queue.put(child_id)
                    
                    processed_count += 1
                    if processed_count % 50 == 0:
                        print(f"  Progress: {processed_count} nodes synced... Queue size: {queue.qsize()}")
                    
                    queue.task_done()
                    # 缓解压力
                    await asyncio.sleep(0.05)
                except Exception as e:
                    print(f"Worker Error: {e}")
                    # traceback.print_exc()

        # 启动并发 workers
        # 为了更简单的终止逻辑，我使用传统的 while 循环配合 queue
        # 注意: 这种简单的 worker 架构需要处理何时停止。
        # 我们可以检查 queue 是否为空且没有正在进行的任务。
        
        # 重新实现 worker 逻辑以便更好地处理并发停止
        async def improved_worker(name):
            nonlocal processed_count
            while True:
                current_id = await queue.get()
                try:
                    if current_id in processed_ids:
                        continue
                    
                    # Fetch
                    data = await page.evaluate(js_fetch_children, current_id)
                    processed_ids.add(current_id)
                    
                    if data:
                        parent = all_nodes[current_id]
                        for item in data:
                            cid = item.get("category_id")
                            cname = item.get("category_name")
                            if cid and cid not in all_nodes:
                                cnode = {
                                    "id": cid, "name": cname.strip(), 
                                    "parent_id": current_id, "children": [], 
                                    "level": parent["level"] + 1
                                }
                                all_nodes[cid] = cnode
                                parent["children"].append(cnode)
                                await queue.put(cid)
                    
                    processed_count += 1
                    if processed_count % 100 == 0:
                        print(f"[{name}] {processed_count} nodes... Q: {queue.qsize()}")
                finally:
                    queue.task_done()
                    await asyncio.sleep(0.05)

        workers = [asyncio.create_task(improved_worker(f"W{i}")) for i in range(CONCURRENCY)]
        
        # 等待队列完成
        await queue.join()
        
        # 停止所有 worker
        for w in workers:
            w.cancel()
            
        # 3. 组装并保存
        tree = [node for node in all_nodes.values() if node["parent_id"] is None]
        out_path = "d:/item/ProSourcing/output/algatop_full_tree.json"
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)
            
        print(f"Extraction complete! Total unique nodes: {len(all_nodes)}")
        print(f"Structure saved to {out_path}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_recursive_sync_parallel())
