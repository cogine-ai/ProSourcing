import asyncio
from playwright.async_api import async_playwright

async def check_storage():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = None
        for p_obj in browser.contexts[0].pages:
            if "algatop.kz" in p_obj.url:
                page = p_obj
                break
                
        if not page:
            print("Target page not found")
            return
            
        js = '''
        () => {
            return {
                local: { ...localStorage },
                session: { ...sessionStorage }
            };
        }
        '''
        res = await page.evaluate(js)
        print("Storage contents:")
        for key, val in res.get("local", {}).items():
            # truncate long values
            print(f"LOCAL [{key}]: {val[:100]}")
            
        for key, val in res.get("session", {}).items():
            print(f"SESSION [{key}]: {val[:100]}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_storage())
