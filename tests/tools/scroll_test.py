import asyncio
from playwright.async_api import async_playwright

async def scroll_table_and_extract():
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
            
        print("Finding scrollable container...")
        js_find_container = '''
        () => {
            const containers = document.querySelectorAll('div');
            for (const c of containers) {
                if (c.scrollHeight > c.clientHeight && c.scrollTop !== undefined) {
                    // Check if it's the table wrapper
                    if (c.querySelector('table')) {
                        return c.className; // returns the class name of the scrollable box
                    }
                }
            }
            return null;
        }
        '''
        
        container_class = await page.evaluate(js_find_container)
        print(f"Scrollable container class: {container_class}")
        
        # Scroll the container down multiple times
        js_scroll = '''
        async () => {
            const c = Array.from(document.querySelectorAll('div')).find(x => x.querySelector('table') && x.scrollHeight > x.clientHeight);
            if (!c) return 0;
            
            let lastHeight = c.scrollTop;
            let stuckCount = 0;
            let loop = 0;
            
            while(stuckCount < 5 && loop < 50) {
                c.scrollTop = c.scrollHeight;
                await new Promise(res => setTimeout(res, 800));
                
                if (c.scrollTop === lastHeight) {
                    stuckCount++;
                } else {
                    stuckCount = 0;
                    lastHeight = c.scrollTop;
                }
                loop++;
            }
            
            return document.querySelectorAll('tr').length;
        }
        '''
        
        print("Scrolling table down to the bottom to load all unexpanded nodes...")
        final_row_count = await page.evaluate(js_scroll)
        print(f"Scrolling finished. Total DOM rows are now: {final_row_count}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scroll_table_and_extract())
