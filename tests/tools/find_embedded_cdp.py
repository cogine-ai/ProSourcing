import asyncio
import json
import re
from playwright.async_api import async_playwright

async def find_embedded_data():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = None
        for p_obj in browser.contexts[0].pages:
            if p_obj.url == "https://app.algatop.kz/niche":
                page = p_obj
                break
                
        if not page:
            return
            
        html = await page.content()
        print(f"Total HTML size: {len(html)}")
        
        # Look for script tags with JSON
        scripts = await page.evaluate('''
            () => Array.from(document.querySelectorAll('script')).map(s => {
                return {
                    id: s.id,
                    type: s.type,
                    len: s.innerHTML.length,
                    content: s.innerHTML.substring(0, 100)
                }
            })
        ''')
        
        for s in scripts:
            if s['len'] > 1000:
                print(f"LARGE SCRIPT: type={s['type']}, id={s['id']}, len={s['len']}")
                print(f"Content start: {s['content']}")
                
        # Also check window variables
        win_vars = await page.evaluate('''
            () => {
                const results = [];
                for (let key in window) {
                    if (key.startsWith('__NEXT_DATA__') || key.includes('STATE') || key.includes('DATA')) {
                        try {
                            const val = JSON.stringify(window[key]);
                            if (val && val.length > 500) {
                                results.push({ key, len: val.length });
                            }
                        } catch(e) {}
                    }
                }
                return results;
            }
        ''')
        print("Window vars:", win_vars)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_embedded_data())
