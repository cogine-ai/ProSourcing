import asyncio
from playwright.async_api import async_playwright

async def check_pagination():
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
            
        print("Looking for pagination controls...")
        
        # Look for buttons that might be pagination
        js = '''
        () => {
            const buttons = Array.from(document.querySelectorAll('button'));
            return buttons.map(b => ({
                text: b.innerText.trim(),
                className: b.className
            })).filter(b => b.text.length > 0 && b.text.length < 50);
        }
        '''
        res = await page.evaluate(js)
        print("Buttons found:")
        for r in res:
            print(f" - {r['text']} (Class: {r['className']})")
        
        # Look for typical pagination components in MUI
        pagination = await page.evaluate('''
            () => {
                const p = document.querySelector('.MuiTablePagination-root, .MuiPagination-root');
                return p ? p.innerText : "No standard MUI pagination found";
            }
        ''')
        print(f"Pagination block: {pagination}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_pagination())
