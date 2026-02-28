import asyncio
from scrapers.algatop_scraper import AlgatopScraper

async def probe_login_page():
    scraper = AlgatopScraper()
    await scraper.init_browser(headless=False) 
    try:
        # 尝试增加超时时间，并使用 domcontentloaded 替代 networkidle
        url = "https://app.algatop.kz/auth/login/mail"
        print(f"Navigating to {url} with 60s timeout...")
        await scraper.page.goto(url, timeout=60000, wait_until="domcontentloaded") 
        await asyncio.sleep(10) 
        
        await scraper.page.screenshot(path="login_page_retry.png")
        print("Screenshot saved to login_page_retry.png")
        
        # 即使加载慢，也尝试探测 input
        inputs = await scraper.page.query_selector_all('input')
        print(f"Found {len(inputs)} input elements")
        for idx, input_el in enumerate(inputs):
            name = await input_el.get_attribute('name')
            type_attr = await input_el.get_attribute('type')
            print(f"Input {idx}: name='{name}', type='{type_attr}'")

    except Exception as e:
        print(f"Error: {e}")
        # 如果 app. 子域名不行，尝试主域名下的登录页探测
        try:
             print("Trying main domain login page...")
             await scraper.page.goto("https://algatop.kz/login", timeout=60000)
             title = await scraper.page.title()
             print(f"Main Login Page Title: {title}")
        except:
            pass
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(probe_login_page())
