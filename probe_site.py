import asyncio
from scrapers.algatop_scraper import AlgatopScraper

async def probe():
    scraper = AlgatopScraper()
    await scraper.init_browser(headless=False) 
    try:
        print("Navigating to Algatop.kz...")
        # 强制使用 .kz 域名
        await scraper.page.goto("https://algatop.kz/") 
        await asyncio.sleep(10) 
        title = await scraper.page.title()
        print(f"Page Title: {title}")
        await scraper.page.screenshot(path="probe_algatop_kz.png")
        print("Screenshot saved to probe_algatop_kz.png")
    except Exception as e:
        print(f"Error during probe: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(probe())
