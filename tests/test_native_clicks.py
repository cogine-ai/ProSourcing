import asyncio
import json
import time
from playwright.async_api import async_playwright

async def expand_native_clicks():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = None
        for p_obj in browser.contexts[0].pages:
            if "algatop.kz/niche" in p_obj.url:
                page = p_obj
                break
                
        if not page:
            print("Target page not found")
            return
            
        print("Using Playwright native clicks to expand tree...")
        
        # Function to get all clickable SVGs that haven't been expanded
        async def get_expandable_svgs():
            # In MUI tables, expand svgs are usually in the first TD
            return await page.evaluate('''
                () => {
                    const rows = Array.from(document.querySelectorAll('tr'));
                    const result = [];
                    for (let i = 0; i < rows.length; i++) {
                        const r = rows[i];
                        const link = r.querySelector('a[href*="/niche/category/"]');
                        if (!link) continue;
                        const idMatch = link.href.match(/\\/category\\/(\\d+)/);
                        if (!idMatch) continue;
                        
                        const svg = r.querySelector('svg');
                        if (svg) {
                            // Check if it's already expanded by looking at the transform matrix
                            const style = window.getComputedStyle(svg);
                            const isExpanded = style.transform && style.transform !== 'none' && style.transform !== 'matrix(1, 0, 0, 1, 0, 0)';
                            
                            if (!window.clickedIds) window.clickedIds = new Set();
                            
                            if (!isExpanded && !window.clickedIds.has(idMatch[1])) {
                                result.push({ index: i, id: idMatch[1] });
                            }
                        }
                    }
                    return result;
                }
            ''')
            
        pass_count = 0
        while pass_count < 5: # Limit passes for this test script
            expandableList = await get_expandable_svgs()
            if not expandableList:
                print("No more items to expand!")
                break
                
            print(f"Pass {pass_count}: Found {len(expandableList)} items to expand.")
            
            for item in expandableList:
                row_idx = item['index']
                cat_id = item['id']
                try:
                    # Find the specific SVG inside the specific row using xpath or locator
                    # nth(row_idx) on 'tr' might be flaky if rows change, but we will click them one by one
                    locator = page.locator(f'tr:has(a[href*="/niche/category/{cat_id}"]) svg').first
                    await locator.scroll_into_view_if_needed()
                    await locator.click(timeout=2000)
                    
                    # Mark as clicked in JS context
                    await page.evaluate(f'''() => {{
                        if (!window.clickedIds) window.clickedIds = new Set();
                        window.clickedIds.add("{cat_id}");
                    }}''')
                    
                    print(f"Clicked {cat_id}")
                    await asyncio.sleep(0.5) # Short wait after each click to let UI react
                except Exception as e:
                    print(f"Failed to click {cat_id}: {e}")
                    
            print(f"Waiting 2s for all API responses for Pass {pass_count}...")
            await asyncio.sleep(2)
            pass_count += 1
            
        print("Done expanding for now.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(expand_native_clicks())
