import asyncio
import json
from playwright.async_api import async_playwright

async def build_tree_from_dom():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = None
        for p_obj in browser.contexts[0].pages:
            if p_obj.url == "https://app.algatop.kz/niche":
                page = p_obj
                break
                
        if not page:
            print("Target page not found")
            return
            
        print("Starting DOM expansion. This will be much faster by clicking all at once per level...")
        
        js_expand = '''
        async () => {
            window.expandedIds = window.expandedIds || new Set();
            
            let passCount = 0;
            while (passCount < 20) { // Safety limit for depth/passes
                let clickedCount = 0;
                const rows = Array.from(document.querySelectorAll('tr'));
                for (const r of rows) {
                    const link = r.querySelector('a[href*="/niche/category/"]');
                    if (!link) continue;
                    const idMatch = link.href.match(/\\/category\\/(\\d+)/);
                    if (!idMatch) continue;
                    const id = idMatch[1];
                    
                    const svg = r.querySelector('svg');
                    if (!svg) continue;
                    
                    if (!window.expandedIds.has(id)) {
                        let target = svg;
                        if (svg.parentElement.tagName.toLowerCase() === 'div' || svg.parentElement.tagName.toLowerCase() === 'span') {
                            target = svg.parentElement;
                        }
                        
                        target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                        window.expandedIds.add(id);
                        clickedCount++;
                    }
                }
                
                if (clickedCount === 0) {
                    // Double check if any are still loading or if we missed any
                    await new Promise(res => setTimeout(res, 2000));
                    const newRows = Array.from(document.querySelectorAll('tr'));
                    let stillNeedExpand = false;
                    for (const r of newRows) {
                        const link = r.querySelector('a[href*="/niche/category/"]');
                        if (!link) continue;
                        const idMatch = link.href.match(/\\/category\\/(\\d+)/);
                        if (!idMatch) continue;
                        const svg = r.querySelector('svg');
                        if (svg && !window.expandedIds.has(idMatch[1])) {
                            stillNeedExpand = true;
                            break;
                        }
                    }
                    if (!stillNeedExpand) break; // Truly done
                } else {
                    console.log(`Pass ${passCount}: Clicked ${clickedCount} nodes. Waiting for loading...`);
                    await new Promise(res => setTimeout(res, 2500)); // wait for all triggered network requests
                }
                passCount++;
            }
            
            console.log("Building tree...");
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
                
                let paddingStr = "0";
                const firstCell = r.querySelector('td, th');
                if (firstCell && firstCell.firstElementChild) {
                   paddingStr = firstCell.firstElementChild.style.paddingLeft || "0rem";
                } else if (firstCell) {
                   paddingStr = window.getComputedStyle(firstCell).paddingLeft || "0px";
                }
                
                const pxVal = parseFloat(paddingStr) || 0;
                
                const node = { id, name, parent_id: null, level: 0, paddingPx: pxVal, children: [] };
                
                while (stack.length > 0 && stack[stack.length - 1].paddingPx >= pxVal) {
                    stack.pop();
                }
                
                if (stack.length > 0) {
                    node.parent_id = stack[stack.length - 1].id;
                    node.level = stack.length;
                    stack[stack.length - 1].children.push(node);
                } else {
                    tree.push(node);
                }
                
                stack.push(node);
            }
            
            return tree;
        }
        '''
        
        try:
            page.set_default_timeout(600000)
            tree = await page.evaluate(js_expand)
            with open("d:/item/ProSourcing/output/algatop_full_tree.json", "w", encoding="utf-8") as f:
                json.dump(tree, f, indent=2, ensure_ascii=False)
            print(f"Extraction complete! Saved {len(tree)} root nodes to algatop_full_tree.json")
        except Exception as e:
            print("Error during evaluate:", e)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(build_tree_from_dom())
