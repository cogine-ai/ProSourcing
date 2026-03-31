import asyncio
import json
import traceback
from playwright.async_api import async_playwright

async def test_api_fetch():
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
            
        print("Testing API fetch via browser context...")
        
        # Test fetching category 00002 (Телефоны и гаджеты)
        js_fetch = '''
        async () => {
            const startDate = "20230101"; // Or something recent, API usually wants dates
            const endDate = "20261231";
            
            // The API url we saw before
            const url = `/api/v1/niche/categoryListStatistic?categoryId=00002`;
            
            const res = await fetch(url, {
                headers: {
                    // Try with the hardcoded top-l we saw before, or no special headers
                    "top-l": "2s3dfnfRgn43PkgmPolqre#",
                    "accept": "application/json, text/plain, */*"
                }
            });
            
            if(!res.ok) return {error: res.status + " " + res.statusText};
            return await res.json();
        }
        '''
        
        try:
            result = await page.evaluate(js_fetch)
            print("API Result:", json.dumps(result)[:500])
        except Exception as e:
            print("Error parsing evaluate:", e)
            traceback.print_exc()
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_api_fetch())
