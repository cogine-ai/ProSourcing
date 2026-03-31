import asyncio
import json
import os
from playwright.async_api import async_playwright

async def run_full_extraction():
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
            
        print("Starting generalized click expansion...")
        
        max_clicks = 8000
        clicks = 0
        consecutive_failures = 0
        
        while clicks < max_clicks:
            try:
                js_find_next = '''
                () => {
                    if (!window.clickedExpandedIds) window.clickedExpandedIds = new Set();
                    
                    const rows = Array.from(document.querySelectorAll('tr'));
                    for (let i = 0; i < rows.length; i++) {
                        const r = rows[i];
                        const link = r.querySelector('a[href*="/niche/category/"]');
                        if (!link) continue;
                        const idMatch = link.href.match(/\\/category\\/(\\d+)/);
                        if (!idMatch) continue;
                        const id = idMatch[1];
                        
                        // Find the expand SVG. It's usually the first SVG in the row padding container.
                        const svgs = Array.from(r.querySelectorAll('svg'));
                        let expandSvg = null;
                        for (const s of svgs) {
                            if (s.className.baseVal && !s.className.baseVal.includes("b24")) {
                                expandSvg = s;
                                break;
                            }
                        }
                        
                        if (!expandSvg) continue;
                        
                        const style = window.getComputedStyle(expandSvg);
                        // Expanded arrows in MUI often rotate 90 deg (matrix(..., 0, 1, -1, 0, ...))
                        const isExpanded = style.transform && style.transform !== 'none' && style.transform !== 'matrix(1, 0, 0, 1, 0, 0)';
                        
                        if (!isExpanded && !window.clickedExpandedIds.has(id)) {
                            return { id: id, index: i };
                        }
                    }
                    return null;
                }
                '''
                
                target_info = await page.evaluate(js_find_next)
                
                if not target_info:
                    print(f"No more expandable nodes found! Fully expanded after {clicks} clicks.")
                    break
                    
                cat_id = target_info['id']
                row_idx = target_info['index']
                
                js_click = f'''
                () => {{
                    const rows = Array.from(document.querySelectorAll('tr'));
                    const r = rows[{row_idx}];
                    if (!r) return false;
                    const svgs = Array.from(r.querySelectorAll('svg'));
                    let target = null;
                    for (const s of svgs) {{
                        if (s.className.baseVal && !s.className.baseVal.includes("b24")) {{
                            target = s;
                            break;
                        }}
                    }}
                    if (!target) return false;
                    
                    if (target.parentElement.tagName.toLowerCase() === 'div' || target.parentElement.tagName.toLowerCase() === 'span') {{
                        target = target.parentElement;
                    }}
                    
                    target.scrollIntoView({{ behavior: "instant", block: "center" }});
                    if (typeof target.click === 'function') {{
                        target.click();
                    }} else {{
                        target.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true, cancelable: true, view: window }}));
                        target.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true, cancelable: true, view: window }}));
                        target.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true, view: window }}));
                    }}
                    
                    window.clickedExpandedIds.add("{cat_id}");
                    return true;
                }}
                '''
                
                success = await page.evaluate(js_click)
                if success:
                    clicks += 1
                    consecutive_failures = 0
                    if clicks % 50 == 0:
                        print(f"Expanded {clicks} nodes...")
                else:
                    consecutive_failures += 1
                    
                await asyncio.sleep(0.3) 
                
            except Exception as e:
                consecutive_failures += 1
                await asyncio.sleep(1)
                
            if consecutive_failures > 10:
                print(f"Too many consecutive failures. Breaking.")
                break
            
        print(f"Expansion finished. Clicks: {clicks}. Building tree from DOM...")
        
        js_build = '''
        () => {
            const tree = [];
            let stack = []; // To keep track of the current parent hierarchy
            
            const finalRows = Array.from(document.querySelectorAll('tr'));
            for (const r of finalRows) {
                const link = r.querySelector('a[href*="/niche/category/"]');
                if (!link) continue;
                const idMatch = link.href.match(/\\/category\\/(\\d+)/);
                if (!idMatch) continue;
                
                const id = idMatch[1];
                const name = link.innerText.trim();
                
                // Get padding to determine depth Level
                let paddingStr = "0rem";
                const firstCell = r.querySelector('td, th');
                if (firstCell && firstCell.firstElementChild) {
                   paddingStr = firstCell.firstElementChild.style.paddingLeft || "0rem";
                }
                
                // e.g. "0rem" -> 0, "2rem" -> 1, "4rem" -> 2
                let paddingVal = parseFloat(paddingStr.replace('rem', '')) || 0;
                let nodeLevel = Math.round(paddingVal / 2);
                
                const node = { id, name, parent_id: null, level: nodeLevel, children: [] };
                
                // Pop elements off the stack that are deeper or at the same level as the current node
                while (stack.length > 0 && stack[stack.length - 1].level >= nodeLevel) {
                    stack.pop();
                }
                
                if (stack.length > 0) {
                    node.parent_id = stack[stack.length - 1].id;
                    stack[stack.length - 1].children.push(node);
                } else {
                    tree.push(node); // It's a root node
                }
                
                stack.push(node);
            }
            
            return tree;
        }
        '''
        
        tree = await page.evaluate(js_build)
        out_path = "d:/item/ProSourcing/output/algatop_full_tree.json"
        
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)
            
        print(f"Extraction complete! Saved {len(tree)} root nodes to {out_path}")
        
        def count_nodes(nodes):
            count = len(nodes)
            for n in nodes:
                count += count_nodes(n['children'])
            return count
            
        print(f"Total nodes in tree: {count_nodes(tree)}")
        
        # Verify if parent_id exists for children
        flat_list = []
        def flatten(n):
            flat_list.append(n)
            for c in n['children']: flatten(c)
        for t in tree: flatten(t)
        
        leaves = [x for x in flat_list if not x['children']]
        print(f"Total leaves: {len(leaves)}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_full_extraction())
