import asyncio
from playwright.async_api import async_playwright

async def debug_page():
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
            
        title = await page.title()
        print(f"Page Title: {title}")
        
        # Check what SVGs are present
        svgs = await page.evaluate('''
            () => Array.from(document.querySelectorAll('svg')).map(s => s.className.baseVal || s.className).slice(0, 50)
        ''')
        print(f"SVGs found: {svgs}")
        
        rows = await page.evaluate('''
            () => Array.from(document.querySelectorAll('tr')).slice(0, 5).map(r => r.innerHTML.substring(0, 150))
        ''')
        print(f"Rows found: {rows}")
        
        links = await page.evaluate('''
            () => Array.from(document.querySelectorAll('a[href*="/niche/category/"]')).slice(0, 10).map(l => l.href + ' ' + l.innerText)
        ''')
        print(f"Links found: {links}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page())
