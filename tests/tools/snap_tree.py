import asyncio
from playwright.async_api import async_playwright

async def snap():
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
                
        if page:
            # expand 00002 just in case
            await page.evaluate('''() => {
                const svgs = document.querySelectorAll('tr svg:not([class*="b24"])');
                if (svgs.length > 0 && svgs[0].parentElement) {
                    svgs[0].parentElement.click();
                }
            }''')
            await asyncio.sleep(2)
            await page.screenshot(path="d:/item/ProSourcing/output/algatop_tree_snap.png", full_page=True)
            print("Screenshot saved to d:/item/ProSourcing/output/algatop_tree_snap.png")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(snap())
