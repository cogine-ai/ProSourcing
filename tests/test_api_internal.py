import asyncio
from playwright.async_api import async_playwright
import json
import datetime

async def trigger_api_with_auth():
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
            
        print("Executing API fetch inside the authenticated browser...")
        
        # We'll try to fetch the first level (categoryId empty or 0)
        # and then a known category 00002
        
        today = datetime.date.today().strftime("%Y%m%d")
        last_month = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y%m%d")
        
        js_fetch_script = f'''
        async (catId) => {{
            const url = `/api/v1/niche/categoryListStatistic?startDate={last_month}&endDate={today}&categoryId=${{catId}}`;
            try {{
                const res = await fetch(url, {{
                    headers: {{
                        "top-l": "2s3dfnfRgn43PkgmPolqre#",
                        "Accept": "application/json, text/plain, */*"
                    }}
                }});
                if (!res.ok) return {{ status: res.status, text: await res.text() }};
                return await res.json();
            }} catch (e) {{
                return {{ error: e.message }};
            }}
        }}
        '''
        
        print(f"Fetching for cat 00002 (Phones)...")
        res2 = await page.evaluate(js_fetch_script, "00002")
        print("Result for 00002:", json.dumps(res2)[:1000])
        
        if "data" in res2:
            print(f"Success! Found {len(res2['data'])} children for 00002.")
        else:
            print("Failed for 00002.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(trigger_api_with_auth())
