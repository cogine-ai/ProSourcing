import asyncio
from scrapers.algatop_scraper import AlgatopScraper

async def explore_navigation():
    scraper = AlgatopScraper()
    await scraper.init_browser(headless=False)
    try:
        # 使用持久化的 auth.json
        await scraper.page.goto("https://app.algatop.kz/")
        await asyncio.sleep(5)
        
        print("Exploring menu items...")
        menu_items = await scraper.page.locator('ul.nav li a, .menu-item, a.nav-link').all()
        for i, item in enumerate(menu_items):
            text = await item.inner_text()
            href = await item.get_attribute('href')
            print(f"Menu {i}: text='{text.strip()}', href='{href}'")
            
        # 截取主页图辅助判断
        await scraper.page.screenshot(path="dashboard_full.png", full_page=True)
        
        # 尝试查找所有输入框及其 placeholder
        inputs = await scraper.page.locator('input').all()
        print(f"\nFound {len(inputs)} inputs on current page:")
        for idx, inp in enumerate(inputs):
            p = await inp.get_attribute('placeholder')
            print(f"Input {idx}: placeholder='{p}'")

    except Exception as e:
        print(f"Exploration failed: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(explore_navigation())
