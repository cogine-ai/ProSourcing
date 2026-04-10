import os
import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

async def explore_algatop_niches():
    async with async_playwright() as pw:
        # 使用有头模式进行最后的调试，看看页面到底长啥样
        browser = await pw.chromium.launch(headless=True)
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        context = await browser.new_context(
            storage_state="d:/item/ProSourcing/auth.json" if os.path.exists("d:/item/ProSourcing/auth.json") else None,
            user_agent=user_agent
        )
        page = await context.new_page()
        page.set_default_timeout(90000)
        
        print("Opening Algatop Niche List...")
        try:
            # 尝试各种可能的 Niche 列表 URL
            urls = [
                "https://app.algatop.kz/niche",
                "https://app.algatop.kz/niche/list",
                "https://app.algatop.kz/categories"
            ]
            
            for url in urls:
                print(f"Trying URL: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(5)
                
                # 截图存证
                filename = f"d:/item/ProSourcing/explore_{url.split('/')[-1]}.png"
                await page.screenshot(path=filename)
                
                # 寻找页面上的链接
                links = await page.locator('a').all()
                print(f"Found {len(links)} links on {url}")
                
                # 寻找包含“Yoga”或“Йога”的链接
                for link in links:
                    text = await link.inner_text()
                    href = await link.get_attribute('href')
                    if any(kw in text.lower() for kw in ["yoga", "йога", "мат"]):
                        print(f"!!! MATCH FOUND: {text} -> {href}")
            
            # 如果都没找到，尝试模拟点击左侧菜单的“Поиск ниши”
            print("Attempting to click sidebar menu 'Поиск ниши'...")
            menu_item = page.locator('text=/Поиск ниши/i').first
            if await menu_item.count() > 0:
                await menu_item.click()
                await asyncio.sleep(5)
                await page.screenshot(path="d:/item/ProSourcing/after_menu_click.png")
                # 再次检测 input
                inputs = await page.locator('input').all()
                print(f"After click, found {len(inputs)} inputs.")
            
        except Exception as e:
            print(f"Exploration failed: {e}")
            await page.screenshot(path="d:/item/ProSourcing/explore_failed.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(explore_algatop_niches())
