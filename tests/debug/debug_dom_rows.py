import asyncio
from playwright.async_api import async_playwright

async def debug_rows():
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
            
        js_get_rows = '''
        () => {
            const rows = Array.from(document.querySelectorAll('tr'));
            return rows.slice(0, 3).map(r => {
                const link = r.querySelector('a');
                let svgHtml = "NO SVG";
                const svg = r.querySelector('svg');
                if (svg) {
                    // Ignore chat icon
                    if (!svg.className.baseVal || !svg.className.baseVal.includes("b24")) {
                        svgHtml = svg.outerHTML;
                    }
                }
                
                return {
                    link: link ? link.outerHTML : "NO LINK",
                    svg: svgHtml,
                    td1: r.querySelector('td') ? r.querySelector('td').innerHTML : "NO TD"
                };
            });
        }
        '''
        
        info = await page.evaluate(js_get_rows)
        import json
        print(json.dumps(info, indent=2, ensure_ascii=False))
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_rows())
