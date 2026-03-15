import asyncio
from playwright.async_api import async_playwright
import json

async def analyze_all_tabs():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        results = []
        for p_obj in browser.contexts[0].pages:
            if "algatop.kz" in p_obj.url:
                js = '''
                () => {
                    const links = Array.from(document.querySelectorAll('a[href*="/niche/category/"]'));
                    const tableRows = Array.from(document.querySelectorAll('tr, div[role="row"]'));
                    const expIcon = Array.from(document.querySelectorAll('.ant-table-row-expand-icon, svg'));
                    return {
                        url: window.location.href,
                        title: document.title,
                        linkCount: links.length,
                        rowCount: tableRows.length,
                        expIconCount: expIcon.length,
                        firstLinkContent: links.length > 0 ? links[0].outerHTML : null,
                        firstRowContent: tableRows.length > 0 ? tableRows[0].innerHTML.substring(0, 300) : null
                    };
                }
                '''
                try:
                    res = await p_obj.evaluate(js)
                    results.append(res)
                except Exception as e:
                    results.append({"url": p_obj.url, "error": str(e)})
                    
        with open("d:/item/ProSourcing/core/dom_analysis.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(analyze_all_tabs())
