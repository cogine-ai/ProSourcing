import asyncio
from scrapers.algatop_scraper import AlgatopScraper

async def probe_login_page():
    scraper = AlgatopScraper()
    await scraper.init_browser(headless=False) 
    try:
        url = "https://app.algatop.kz/auth/login/mail"
        print(f"Navigating to {url}...")
        await scraper.page.goto(url) 
        await asyncio.sleep(5) 
        
        # 截取登录页面的图
        await scraper.page.screenshot(path="login_page_probe.png")
        print("Screenshot saved to login_page_probe.png")
        
        # 打印页面中的所有 input 元素及其属性，用于精准定位
        inputs = await scraper.page.query_selector_all('input')
        print(f"Found {len(inputs)} input elements:")
        for idx, input_el in enumerate(inputs):
            name = await input_el.get_attribute('name')
            type_attr = await input_el.get_attribute('type')
            placeholder = await input_el.get_attribute('placeholder')
            print(f"Input {idx}: name='{name}', type='{type_attr}', placeholder='{placeholder}'")
            
        # 打印页面中的按钮
        buttons = await scraper.page.query_selector_all('button')
        print(f"Found {len(buttons)} button elements:")
        for idx, button in enumerate(buttons):
            text = await button.inner_text()
            print(f"Button {idx}: text='{text.strip()}'")

    except Exception as e:
        print(f"Error during login probe: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(probe_login_page())
