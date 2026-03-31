import asyncio
import json
import time
from playwright.async_api import async_playwright

async def run_virtualized_extraction():
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
            
        print("Starting Virtualized Tree Extraction...")
        
        # 1. 自动展开所有节点 (需要边滚动边点击)
        async def expand_all():
            print("Phase 1: Expanding all nodes via scrolling...")
            clicked_ids = set()
            scroll_count = 0
            stuck_passes = 0
            
            while stuck_passes < 10:
                # 获取当前可见的、未展开的箭头
                # 注意：MUI 展开后 SVG 通常会有 transform: rotate(90deg)
                targets = await page.evaluate('''
                    () => {
                        const results = [];
                        const rows = Array.from(document.querySelectorAll('tr'));
                        rows.forEach((r, idx) => {
                            const link = r.querySelector('a[href*="/niche/category/"]');
                            if (!link) return;
                            const id = link.href.match(/\\/category\\/(\\d+)/)[1];
                            const svg = Array.from(r.querySelectorAll('svg')).find(s => !s.className.baseVal.includes("b24"));
                            if (svg) {
                                const style = window.getComputedStyle(svg);
                                const isExpanded = style.transform && style.transform !== 'none' && style.transform !== 'matrix(1, 0, 0, 1, 0, 0)';
                                if (!isExpanded) {
                                    results.push({ id, index: idx });
                                }
                            }
                        });
                        return results;
                    }
                ''')
                
                new_clicks = [t for t in targets if t['id'] not in clicked_ids]
                if new_clicks:
                    print(f"  Found {len(new_clicks)} nodes to expand at current view.")
                    for target in new_clicks:
                        # 点击
                        await page.evaluate(f'''
                            (idx) => {{
                                const rows = document.querySelectorAll('tr');
                                if (rows[idx]) {{
                                    const svg = Array.from(rows[idx].querySelectorAll('svg')).find(s => !s.className.baseVal.includes("b24"));
                                    if (svg && svg.parentElement) svg.parentElement.click();
                                }}
                            }}
                        ''', target['index'])
                        clicked_ids.add(target['id'])
                    
                    stuck_passes = 0
                    await asyncio.sleep(1.5) # 等待渲染
                else:
                    # 尝试滚动
                    print("  No unexpanded nodes in view, scrolling...")
                    c_exists = await page.evaluate('''
                        () => {
                            const c = Array.from(document.querySelectorAll('div')).find(x => x.querySelector('table') && x.scrollHeight > x.clientHeight);
                            if (c) {
                                c.scrollTop += 300;
                                return true;
                            }
                            return false;
                        }
                    ''')
                    if not c_exists:
                        print("  Scrollable container not found or at bottom.")
                        break
                    
                    scroll_count += 1
                    stuck_passes += 1
                    await asyncio.sleep(0.8)
            
            print(f"Expansion pass finished. Total unique clicks: {len(clicked_ids)}")

        # 2. 收集所有数据 (虚拟列表需要通过滚动采集并去重)
        async def collect_data():
            print("Phase 2: Collecting all nodes via incremental scrolling...")
            all_nodes = {} # id -> node
            
            # 回到顶部
            await page.evaluate('''
                () => {
                    const c = Array.from(document.querySelectorAll('div')).find(x => x.querySelector('table') && x.scrollHeight > x.clientHeight);
                    if (c) c.scrollTop = 0;
                }
            ''')
            await asyncio.sleep(1)
            
            last_top = -1
            while True:
                # 获取当前可见行
                rows = await page.evaluate('''
                    () => {
                        const results = [];
                        const rows = Array.from(document.querySelectorAll('tr'));
                
                        rows.forEach(r => {
                            const link = r.querySelector('a[href*="/niche/category/"]');
                            if (!link) return;
                            
                            const id = link.href.match(/\\/category\\/(\\d+)/)[1];
                            const name = link.innerText.trim();
                            
                            let paddingStr = "0rem";
                            const firstCell = r.querySelector('td, th');
                            if (firstCell && firstCell.firstElementChild) {
                               paddingStr = firstCell.firstElementChild.style.paddingLeft || "0rem";
                            }
                            let paddingVal = parseFloat(paddingStr.replace('rem', '')) || 0;
                            let nodeLevel = Math.round(paddingVal / 2);
                            
                            results.push({ id, name, level: nodeLevel });
                        });
                        return results;
                    }
                ''')
                
                for r in rows:
                    if r['id'] not in all_nodes:
                        all_nodes[r['id']] = r
                
                # 滚动
                scroll_info = await page.evaluate('''
                    () => {
                        const c = Array.from(document.querySelectorAll('div')).find(x => x.querySelector('table') && x.scrollHeight > x.clientHeight);
                        if (!c) return null;
                        c.scrollTop += 200;
                        return { top: c.scrollTop, height: c.scrollHeight, client: c.clientHeight };
                    }
                ''')
                
                if not scroll_info or scroll_info['top'] == last_top:
                    break
                
                last_top = scroll_info['top']
                await asyncio.sleep(0.3)
                
            print(f"Collection finished. Total unique nodes found: {len(all_nodes)}")
            return list(all_nodes.values())

        # await expand_all() # 暂时只采集显示的，如果还是不全再深度扩展
        # 实际上我们要的是全量，所以必须 expand_all
        await expand_all()
        nodes_list = await collect_data()
        
        # 重新构建树结构 (因为是按滚动顺序来的，可以直接利用之前的栈逻辑)
        def build_tree(flat_list):
            tree = []
            stack = []
            for item in flat_list:
                node = { **item, "parent_id": None, "children": [] }
                
                while stack and stack[-1]['level'] >= node['level']:
                    stack.pop()
                
                if stack:
                    node['parent_id'] = stack[-1]['id']
                    stack[-1]['children'].append(node)
                else:
                    tree.append(node)
                
                stack.append(node)
            return tree

        tree = build_tree(nodes_list)
        
        out_path = "d:/item/ProSourcing/output/algatop_full_tree.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)
            
        print(f"Saved {len(nodes_list)} nodes to {out_path}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_virtualized_extraction())
