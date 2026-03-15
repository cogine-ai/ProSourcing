import asyncio
import json
from playwright.async_api import async_playwright

async def build_tree_from_dom(page):
    print("Building tree from DOM...")
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
    out_path = "d:/item/ProSourcing/output/algatop_full_tree.json"
    
    import os
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(tree, f, indent=2, ensure_ascii=False)
        
    print(f"Extraction complete! Saved to {out_path}")
    
    def count_nodes(nodes):
        count = len(nodes)
        for n in nodes:
            count += count_nodes(n['children'])
        return count
        
    print(f"Total nodes in tree: {count_nodes(tree)}")

async def run_fast():
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
            
        print("Starting fast Python-driven expansion (Parent clicks)...")
        
        clicked_ids = set()
        max_passes = 400
        passes = 0
        
        while passes < max_passes:
            passes += 1
            js_get_targets = '''
            () => {
                const targets = [];
                const rows = Array.from(document.querySelectorAll('tr'));
                for (let i = 0; i < rows.length; i++) {
                    const r = rows[i];
                    const link = r.querySelector('a[href*="/niche/category/"]');
                    if (!link) continue;
                    const idMatch = link.href.match(/\\/category\\/(\\d+)/);
                    if (!idMatch) continue;
                    
                    const svgs = Array.from(r.querySelectorAll('svg'));
                    for (const s of svgs) {
                        if (s.className.baseVal && !s.className.baseVal.includes("b24")) {
                            const style = window.getComputedStyle(s);
                            const isExpanded = style.transform && style.transform !== 'none' && style.transform !== 'matrix(1, 0, 0, 1, 0, 0)';
                            if (!isExpanded) {
                                targets.push({id: idMatch[1], index: i});
                            }
                            break;
                        }
                    }
                }
                return targets;
            }
            '''
            
            targets = await page.evaluate(js_get_targets)
            to_click = [t for t in targets if t['id'] not in clicked_ids]
            
            if not to_click:
                print("No more unexpanded nodes found! Verifying...")
                await asyncio.sleep(4)
                targets_verify = await page.evaluate(js_get_targets)
                if not [t for t in targets_verify if t['id'] not in clicked_ids]:
                    break
                continue
                
            print(f"Pass {passes}: Found {len(to_click)} nodes to expand.")
            
            batch_size = 50
            for i in range(0, len(to_click), batch_size):
                batch = to_click[i:i+batch_size]
                batch_idxs_json = json.dumps([t['index'] for t in batch])
                
                js_click_batch = f'''
                () => {{
                    const batchIdxs = {batch_idxs_json};
                    const rows = Array.from(document.querySelectorAll('tr'));
                    let clickedCount = 0;
                    for (const idx of batchIdxs) {{
                        const r = rows[idx];
                        if (!r) continue;
                        const svgs = Array.from(r.querySelectorAll('svg'));
                        for (const s of svgs) {{
                            if (s.className.baseVal && !s.className.baseVal.includes("b24")) {{
                                let target = s.parentElement; // The div wrapping the svg captures the click in MUI
                                target.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true, cancelable: true, view: window }}));
                                target.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true, cancelable: true, view: window }}));
                                target.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true, view: window }}));
                                clickedCount++;
                                break;
                            }}
                        }}
                    }}
                    return clickedCount;
                }}
                '''
                
                await page.evaluate(js_click_batch)
                for t in batch:
                    clicked_ids.add(t['id'])
                
            print(f"  Clicked {len(to_click)} nodes this pass. Waiting for UI...")
            await asyncio.sleep(2.5) # Wait for network requests
                
        await build_tree_from_dom(page)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_fast())
