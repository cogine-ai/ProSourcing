import asyncio
from playwright.async_api import async_playwright
import json

async def capture_onload():
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
            
        print("Listening for requests on page reload...")
        
        requests = []
        async def handle_request(request):
            if "algatop.kz" in request.url:
                requests.append({
                    "url": request.url,
                    "method": request.method,
                    "headers": dict(request.headers)
                })
                
        page.on("request", handle_request)
        
        # Reload the page
        print("Reloading page...")
        await page.reload(wait_until="networkidle")
        print("Reload finished. Waiting 3 more seconds...")
        await asyncio.sleep(3)
        
        print("\nCaptured ALgatop Requests:")
        for r in requests:
            print(f"[{r['method']}] {r['url']}")
            # If it's an API call, it might be the one
            if "api" in r['url']:
                print(f"  Headers: {json.dumps(r['headers'], indent=2)}")
                print("-" * 30)
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_onload())
