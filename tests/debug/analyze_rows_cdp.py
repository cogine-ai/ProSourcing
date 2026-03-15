import asyncio
from playwright.async_api import async_playwright
import json

async def dump_rows():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = None
        for p_obj in browser.contexts[0].pages:
            if p_obj.url == "https://app.algatop.kz/niche":
                page = p_obj
                break
                
        if not page:
            print("No main niche page")
            return
            
        js = '''
        () => {
            const rows = Array.from(document.querySelectorAll('tr'));
            return rows.filter(r => r.querySelector('a[href*="/niche/category/"]')).map(r => {
                const link = r.querySelector('a[href*="/niche/category/"]');
                const idMatch = link.href.match(/\\/category\\/(\\d+)/);
                
                // padding left of the first cell usually indicates depth
                let padding = "0px";
                let btnHtml = null;
                const firstCell = r.querySelector('td, th');
                if (firstCell) {
                    padding = window.getComputedStyle(firstCell).paddingLeft;
                    // look for the button
                    const btn = firstCell.querySelector('button, svg');
                    if (btn) btnHtml = btn.outerHTML;
                }
                
                return {
                    id: idMatch ? idMatch[1] : null,
                    name: link.innerText.trim(),
                    paddingLeft: padding,
                    htmlSnippet: r.innerHTML.substring(0, 300)
                };
            });
        }
        '''
        res = await page.evaluate(js)
        with open("d:/item/ProSourcing/core/dom_rows.json", "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(dump_rows())
