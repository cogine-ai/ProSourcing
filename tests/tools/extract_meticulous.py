import asyncio
import json
from playwright.async_api import async_playwright

async def run_meticulous_extraction():
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
            
        print("Starting meticulous Python-driven expansion...")
        
        while True:
            # We must scroll to force React/MUI to render virtualized rows if any,
            # but it seems it's not virtualized. Anyway, we find ONE unexpanded node, click it, wait, and repeat.
            # This is slow but 100% reliable. Let's do small batches but ensure they are actually clicked.
            
            js_find_unexpanded = '''
            () => {
                const rows = Array.from(document.querySelectorAll('tr'));
                for (let i = 0; i < rows.length; i++) {
                    const r = rows[i];
                    const link = r.querySelector('a[href*="/niche/category/"]');
                    if (!link) continue;
                    
                    const svgs = Array.from(r.querySelectorAll('svg'));
                    let expandSvg = null;
                    for (const s of svgs) {
                        if (s.className.baseVal && !s.className.baseVal.includes("b24")) {
                            expandSvg = s;
                            break;
                        }
                    }
                    
                    if (expandSvg) {
                        const style = window.getComputedStyle(expandSvg);
                        const isExpanded = style.transform && style.transform !== 'none' && style.transform !== 'matrix(1, 0, 0, 1, 0, 0)';
                        if (!isExpanded) {
                            return {
                                id: link.href.match(/\\/category\\/(\\d+)/)[1],
                                index: i
                            };
                        }
                    }
                }
                return null;
            }
            '''
            
            target = await page.evaluate(js_find_unexpanded)
            
            if not target:
                print("No more unexpanded nodes! Verifying in 3 seconds...")
                await asyncio.sleep(3)
                target_verify = await page.evaluate(js_find_unexpanded)
                if not target_verify:
                    break
                target = target_verify
                
            idx = target['index']
            cat_id = target['id']
            
            print(f"Clicking row {idx} (ID: {cat_id})")
            
            # Click it using Playwright locator to ensure it scrolls and clicks properly
            try:
                # Get the row
                row_loc = page.locator("tr").nth(idx)
                # Find the svg that is NOT the chat icon
                svg_loc = row_loc.locator('svg:not([class*="b24"])').first
                
                await svg_loc.scroll_into_view_if_needed(timeout=1000)
                await asyncio.sleep(0.1)
                
                # Check if bounding box exists
                box = await svg_loc.bounding_box()
                if box:
                    await page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                else:
                    await svg_loc.click(force=True, timeout=1000)
                    
                # Wait for child rows to appear
                await asyncio.sleep(0.6)
            except Exception as e:
                print(f"Failed to click {cat_id} at index {idx}: {e}")
                # Mark it as expanded in JS so we skip it if it's broken
                await page.evaluate(f'''
                    () => {{
                        const row = document.querySelectorAll('tr')[{idx}];
                        if(row) {{
                            const svg = row.querySelector('svg:not([class*="b24"])');
                            if(svg) svg.style.transform = 'rotate(90deg)'; // fake expanded
                        }}
                    }}
                ''')
                
        print("Expansion finished. Building tree...")
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
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)
            
        def count_nodes(nodes):
            count = len(nodes)
            for n in nodes: count += count_nodes(n['children'])
            return count
            
        print(f"Total nodes in tree: {count_nodes(tree)}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_meticulous_extraction())
