import asyncio
import json
from playwright.async_api import async_playwright

async def analyze_dom():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print("Connect error:", e)
            return

        page = None
        for p_obj in browser.contexts[0].pages:
            if "algatop.kz/niche" in p_obj.url:
                page = p_obj
                break
                
        if not page:
            print("No page")
            return

        # Let's see what a row looks like
        js_code = '''
        () => {
            const rows = Array.from(document.querySelectorAll('.ant-table-row, tr[class*="level"]'));
            if (rows.length === 0) return { error: "no rows" };
            
            // Just get the first 5 rows to analyze their classes and structure
            return rows.slice(0, 5).map(r => {
                const link = r.querySelector('a[href*="/niche/category/"]');
                const idMatch = link ? link.href.match(/\\/category\\/(\\d+)/) : null;
                return {
                    className: r.className,
                    id: idMatch ? idMatch[1] : null,
                    name: link ? link.innerText.trim() : null,
                    html: r.innerHTML.substring(0, 200) // snippet
                };
            });
        }
        '''
        
        res = await page.evaluate(js_code)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(analyze_dom())
