import asyncio
from playwright.async_api import async_playwright

async def run_test():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            print("Connected to browser on 9222")
        except Exception as e:
            print(f"Failed to connect: {e}")
            return

        context = browser.contexts[0]
        page = None
        for p_obj in context.pages:
            if "algatop.kz/niche" in p_obj.url:
                page = p_obj
                break
        
        if not page:
            print("Page not found")
            return
            
        print(f"Testing on page: {page.url}")
        
        js_code = '''
        async () => {
            const startDate = "20260211";
            const endDate = "20260311";
            const headers = {
                "top-l": "2s3dfnfRgn43PkgmPolqre#",
                "referer": "https://app.algatop.kz/niche"
            };
            
            const url = `/api/v1/niche/categoryListStatistic?startDate=${startDate}&endDate=${endDate}&categoryId=00002`;
            try {
                const res = await fetch(url, { headers });
                const text = await res.text();
                return { status: res.status, text: text.substring(0, 500) };
            } catch (e) {
                return { error: e.message };
            }
        }
        '''
        
        res = await page.evaluate(js_code)
        print("API Test Result:")
        print(res)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_test())
