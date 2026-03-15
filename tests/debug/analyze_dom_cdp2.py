import asyncio
from playwright.async_api import async_playwright
import json

async def analyze_dom():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print("Connect error:", e)
            return

        for p_obj in browser.contexts[0].pages:
            if "algatop.kz/niche" in p_obj.url:
                print(f"Checking page: {p_obj.url}")
                
                js_code = '''
                () => {
                    const links = Array.from(document.querySelectorAll('a[href*="/niche/category/"]'));
                    if (links.length === 0) return { error: "no category links" };
                    
                    // take first 3 links to inspect their parent DOM tree
                    return links.slice(0, 3).map(l => {
                        let html_chain = [];
                        let curr = l;
                        for(let i=0; i<4; i++) {
                            if (!curr) break;
                            html_chain.push(curr.outerHTML.substring(0, 150));
                            curr = curr.parentElement;
                        }
                        return {
                            text: l.innerText.trim(),
                            href: l.href,
                            chain: html_chain
                        };
                    });
                }
                '''
                res = await p_obj.evaluate(js_code)
                print(json.dumps(res, indent=2, ensure_ascii=False))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(analyze_dom())
