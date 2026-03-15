import asyncio
from playwright.async_api import async_playwright
import json

async def capture_all():
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
            
        print("Listening for ALL requests...")
        
        async def handle_request(request):
            # Ignore images and generic JS to reduce noise
            if not request.url.endswith((".png", ".jpg", ".svg", ".css")):
                print(f"REQUEST: {request.method} {request.url}")
                
        page.on("request", handle_request)
        
        # Click the first unexpanded node
        js_click = '''
        () => {
            const svgs = Array.from(document.querySelectorAll('tr svg'));
            for (const s of svgs) {
                if (s.className.baseVal && !s.className.baseVal.includes("b24")) {
                    const style = window.getComputedStyle(s);
                    const isExpanded = style.transform && style.transform !== 'none' && style.transform !== 'matrix(1, 0, 0, 1, 0, 0)';
                    if (!isExpanded) {
                        s.parentElement.click();
                        return true;
                    }
                }
            }
            return false;
        }
        '''
        
        success = await page.evaluate(js_click)
        if success:
            print("Clicked a node. Waiting 3 seconds for network...")
            await asyncio.sleep(3)
        else:
            print("No unexpanded nodes to click.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_all())
