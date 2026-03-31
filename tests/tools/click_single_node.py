import asyncio
from playwright.async_api import async_playwright

async def click_test():
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
            
        print("Testing click on 00002...")
        # Get the row for 00002
        row_loc = page.locator('tr:has(a[href*="/niche/category/00002"])').first
        
        # Test clicking the SVG parent first
        svg_loc = row_loc.locator('svg:not([class*="b24"])').first
        parent_loc = svg_loc.locator('..')
        
        print("Clicking parent element first...")
        await parent_loc.scroll_into_view_if_needed()
        await parent_loc.click()
        await asyncio.sleep(2)
        
        # Check rows
        rows = await page.locator("tr").count()
        print(f"Total rows after clicking parent: {rows}")
        
        if rows > 20: 
            print("Expansion successful via parent click!")
        else:
            print("Trying direct SVG click...")
            await svg_loc.click()
            await asyncio.sleep(2)
            rows = await page.locator("tr").count()
            print(f"Total rows after clicking SVG: {rows}")

            if rows <= 20:
                print("Trying dispatchEvent on SVG...")
                await page.evaluate('''() => {
                    const row = document.querySelector('tr');
                    const svg = Array.from(row.querySelectorAll('svg')).find(s => !s.className.baseVal.includes("b24"));
                    if(svg) {
                        svg.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                    }
                }''')
                await asyncio.sleep(2)
                rows = await page.locator("tr").count()
                print(f"Total rows after dispatchEvent: {rows}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(click_test())
