import asyncio
import json
from playwright.async_api import async_playwright

async def run_simple():
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
            
        print("Starting simple Python-driven expansion...")
        
        clicked_ids = set()
        
        while True:
            # Get current rows
            rows = await page.locator("tr").all()
            found_unexpanded = False
            
            for i, row in enumerate(rows):
                try:
                    # Get the category ID from the link in this row
                    link_href = await row.locator('a[href*="/niche/category/"]').get_attribute('href', timeout=500)
                    if not link_href:
                        continue
                        
                    cat_id = link_href.split('/')[-1]
                    
                    # See if this row has an SVG that isn't the support chat icon
                    svgs = await row.locator('svg').all()
                    expand_svg = None
                    for svg in svgs:
                        classes = await svg.get_attribute('class') or ""
                        if "b24" not in classes:
                            expand_svg = svg
                            break
                            
                    if not expand_svg:
                        continue
                        
                    # Check if it looks expanded
                    style = await expand_svg.evaluate("el => window.getComputedStyle(el).transform")
                    is_expanded = style and style != 'none' and style != 'matrix(1, 0, 0, 1, 0, 0)'
                    
                    if not is_expanded and cat_id not in clicked_ids:
                        print(f"Clicking {cat_id}")
                        await expand_svg.scroll_into_view_if_needed()
                        await expand_svg.click()
                        clicked_ids.add(cat_id)
                        found_unexpanded = True
                        await asyncio.sleep(0.5) # Wait for UI to update
                        break # Break out of row loop to re-fetch rows, as DOM changed
                        
                except Exception as e:
                    # Stale element or timeout, just skip and refresh rows next loop
                    pass
                    
            if not found_unexpanded:
                # Double check
                await asyncio.sleep(2)
                # Check again logic omitted for brevity, let's assume if we loop through all and find nothing we're done
                print("No more unexpanded nodes found!")
                break
                
        print("Expansion complete. Parsing tree...")
        
        # Now parse the flat list of rows into a tree
        # ... logic will be added here
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_simple())
