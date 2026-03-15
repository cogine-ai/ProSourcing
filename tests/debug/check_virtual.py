import asyncio
from playwright.async_api import async_playwright

async def check_virtualization():
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
            
        print("Checking for virtualization...")
        
        # Count rows currently
        count1 = await page.locator("tr").count()
        print(f"Rows before scroll: {count1}")
        
        # Scroll to bottom smoothly
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)
        
        count2 = await page.locator("tr").count()
        print(f"Rows after scroll down: {count2}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_virtualization())
