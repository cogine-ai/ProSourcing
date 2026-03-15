import asyncio
import json
from playwright.async_api import async_playwright

async def run_final():
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
                
        if not page: return
            
        print("Starting final steady extraction with Load More handling...")
        
        passes = 0
        consecutive_zero = 0
        clicked_ids = set()
        
        while consecutive_zero < 4:
            passes += 1
            js_find = '''
            () => {
                const targets = [];
                const rows = Array.from(document.querySelectorAll('tr'));
                for (let i = 0; i < rows.length; i++) {
                    const r = rows[i];
                    const link = r.querySelector('a[href*="/niche/category/"]');
                    if (!link) continue;
                    const idMatch = link.href.match(/\\/category\\/(\\d+)/);
                    if (!idMatch) continue;
                    const catId = idMatch[1];
                    
                    const svgs = Array.from(r.querySelectorAll('svg'));
                    for (const s of svgs) {
                        if (s.className.baseVal && !s.className.baseVal.includes("b24")) {
                            const style = window.getComputedStyle(s);
                            const isExpanded = style.transform && style.transform !== 'none' && style.transform !== 'matrix(1, 0, 0, 1, 0, 0)';
                            if (!isExpanded) {
                                targets.push({ id: catId, index: i });
                            }
                            break;
                        }
                    }
                }
                return targets;
            }
            '''
            
            targets = await page.evaluate(js_find)
            to_click = [t for t in targets if t['id'] not in clicked_ids][:40] # batch of 40
            
            if not to_click:
                # If no unexpanded nodes, try to click "Show more"
                js_load_more = '''
                () => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const loadMore = buttons.find(b => b.innerText && b.innerText.includes('Показать больше'));
                    if (loadMore) {
                        loadMore.scrollIntoView({ behavior: "auto", block: "center" });
                        loadMore.click();
                        return true;
                    }
                    return false;
                }
                '''
                clicked_load_more = await page.evaluate(js_load_more)
                if clicked_load_more:
                    print("Clicked 'Show more' button. Waiting for rows to load...")
                    await asyncio.sleep(4)
                    consecutive_zero = 0
                    continue
                else:
                    consecutive_zero += 1
                    await asyncio.sleep(2)
                    continue
            
            consecutive_zero = 0
            
            js_click_batch = f'''
            () => {{
                const batchIdxs = {json.dumps([t['index'] for t in to_click])};
                const rows = Array.from(document.querySelectorAll('tr'));
                let count = 0;
                for (const idx of batchIdxs) {{
                    const r = rows[idx];
                    if (!r) continue;
                    const svgs = Array.from(r.querySelectorAll('svg'));
                    for (const s of svgs) {{
                        if (s.className.baseVal && !s.className.baseVal.includes("b24")) {{
                            let target = s.parentElement;
                            if (count === 0) target.scrollIntoView({{ behavior: "auto", block: "center" }});
                            target.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true, cancelable: true, view: window }}));
                            target.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true, cancelable: true, view: window }}));
                            target.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true, view: window }}));
                            count++;
                            break;
                        }}
                    }}
                }}
                return count;
            }}
            '''
            
            await page.evaluate(js_click_batch)
            for t in to_click:
                clicked_ids.add(t['id'])
                
            print(f"Pass {passes}: Clicked {len(to_click)} nodes. Waiting...")
            await asyncio.sleep(1.8)
            
        print("Expansion complete. Parsing tree...")
        js_build = '''
        () => {
            const tree = [];
            let stack = [];
            const finalRows = Array.from(document.querySelectorAll('tr'));
            for (const r of finalRows) {
                const link = r.querySelector('a[href*="/niche/category/"]');
                if (!link) continue;
                const idMatch = link.href.match(/\\/category\\/(\\d+)/);
                if (!idMatch) continue;
                
                const id = idMatch[1];
                const name = link.innerText.trim();
                let paddingStr = "0rem";
                const firstCell = r.querySelector('td, th');
                if (firstCell && firstCell.firstElementChild) {
                   paddingStr = firstCell.firstElementChild.style.paddingLeft || "0rem";
                }
                let paddingVal = parseFloat(paddingStr.replace('rem', '')) || 0;
                let nodeLevel = Math.round(paddingVal / 2);
                
                const node = { id, name, parent_id: null, level: nodeLevel, children: [] };
                while (stack.length > 0 && stack[stack.length - 1].level >= nodeLevel) {
                    stack.pop();
                }
                if (stack.length > 0) {
                    node.parent_id = stack[stack.length - 1].id;
                    stack[stack.length - 1].children.push(node);
                } else {
                    tree.push(node);
                }
                stack.push(node);
            }
            return tree;
        }
        '''
        
        tree = await page.evaluate(js_build)
        
        def count_nodes(nodes):
            count = len(nodes)
            for n in nodes: count += count_nodes(n['children'])
            return count
            
        total = count_nodes(tree)
        print(f"Total nodes in tree: {total}")
        
        import os
        out_path = "d:/item/ProSourcing/output/algatop_full_tree.json"
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)
            
        print(f"Saved to {out_path}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_final())
