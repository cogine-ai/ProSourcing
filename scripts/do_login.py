import asyncio
from scrapers.algatop_scraper import AlgatopScraper

async def run_login():
    scraper = AlgatopScraper()
    # 第一次登录建议开启 headless=False 以便观察是否需要验证码
    await scraper.init_browser(headless=False)
    try:
        print("Starting login process on Algatop.kz...")
        await scraper.login()
        print("Waiting a bit to ensure session is stable...")
        await asyncio.sleep(5)
        await scraper.save_state()
        print("Login completed. auth.json has been created/updated.")
    except Exception as e:
        print(f"Login failed: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(run_login())
