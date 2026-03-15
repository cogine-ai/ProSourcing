import asyncio
from playwright.async_api import async_playwright
import re

async def find_embedded_cat():
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
            
        content = await page.content()
        print(f"Total HTML length: {len(content)}")
        
        # Test for a deep category known to exist
        if "06551" in content:
            print("FOUND ID 06551 in HTML!")
        if "Автомобильные визитки" in content:
            print("FOUND NAME 'Автомобильные визитки' in HTML!")
            
        # Let's count how many times 'niche/category/' appears
        links = re.findall(r'niche/category/\d+', content)
        print(f"Total category links in raw HTML: {len(links)}")
        
        # What about in window variables?
        js_find_in_window = '''
        () => {
            const results = [];
            
            // Helper function to stringify safely and search
            function searchObj(obj, depth=0) {
                if (depth > 6) return;
                try {
                    const str = JSON.stringify(obj);
                    if (str && str.includes("06551")) {
                        results.push("Found 06551 in JSON stringify!");
                    }
                } catch(e) {}
            }
            
            for (let k in window) {
                if (k !== 'window' && k !== 'document') {
                    searchObj(window[k]);
                }
            }
            
            // Also check script tags explicitly
            const scripts = Array.from(document.querySelectorAll('script'));
            for(let i=0; i<scripts.length; i++) {
                if(scripts[i].innerHTML.includes("06551")) {
                    results.push(`Found 06551 in script tag ${i}`);
                }
            }
            
            return results;
        }
        '''
        
        deep = await page.evaluate(js_find_in_window)
        print("Deep search results:", deep)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_embedded_cat())
