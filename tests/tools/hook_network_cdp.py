import asyncio
import json
from playwright.async_api import async_playwright

async def hook_network():
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
            
        print("Listening for API requests... I will click ONE category and log the request.")
        
        request_log = []
        
        async def on_request(request):
            if "categoryListStatistic" in request.url or "category" in request.url or "/api/" in request.url:
                request_log.append({
                    "url": request.url,
                    "method": request.method,
                    "headers": request.headers
                })
                
        page.on("request", on_request)
        
        # Click the first unexpanded svg
        js_click = '''
        () => {
            const row = Array.from(document.querySelectorAll('tr')).find(r => r.querySelector('svg'));
            if (row) {
                const svg = row.querySelector('svg');
                let target = svg;
                if (svg.parentElement.tagName.toLowerCase() === 'div' || svg.parentElement.tagName.toLowerCase() === 'span') {
                    target = svg.parentElement;
                }
                target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                return true;
            }
            return false;
        }
        '''
        
        clicked = await page.evaluate(js_click)
        if clicked:
            print("Clicked a category! Waiting for network...")
            await asyncio.sleep(3)
        else:
            print("No category to click.")
            
        with open("d:/item/ProSourcing/core/network_log.json", "w", encoding="utf-8") as f:
            json.dump(request_log, f, indent=2)
            
        print(f"Logged {len(request_log)} relevant requests to network_log.json")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(hook_network())
