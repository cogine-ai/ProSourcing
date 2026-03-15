import asyncio
from playwright.async_api import async_playwright
import json

async def extract_headers():
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
            
        # Get Cookies
        cookies = await browser.contexts[0].cookies()
        print("\n--- COOKIES ---")
        print(json.dumps(cookies, indent=2))
        
        # Get localStorage
        local_storage = await page.evaluate("() => JSON.stringify(localStorage)")
        print("\n--- LOCAL STORAGE ---")
        print(local_storage[:1000]) # usually has the token
        
        # Look for the 'top-l' header value in localStorage or session
        session_storage = await page.evaluate("() => JSON.stringify(sessionStorage)")
        print("\n--- SESSION STORAGE ---")
        print(session_storage[:1000])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_headers())
