import os
import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

async def debug_niche_page():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        context = await (await pw.chromium.launch()).new_context(
            storage_state="d:/item/ProSourcing/auth.json" if os.path.exists("d:/item/ProSourcing/auth.json") else None,
            user_agent=user_agent
        )
        page = await context.new_page()
        page.set_default_timeout(60000)
        
        print("Navigating to /niche...")
        try:
            await page.goto("https://app.algatop.kz/niche", wait_until="networkidle", timeout=60000)
            print(f"Current URL: {page.url}")
            
            await page.screenshot(path="d:/item/ProSourcing/niche_debug.png")
            
            content = await page.content()
            print(f"Content length: {len(content)}")
            
            # 这里的 input 可能是异步加载的
            print("Looking for inputs...")
            inputs = page.locator('input')
            count = await inputs.count()
            print(f"Found {count} inputs.")
            
            # 尝试等待一个可见的 input
            try:
                print("Waiting for visible input...")
                await page.wait_for_selector('input', state='visible', timeout=10000)
                print("Visible input found!")
            except:
                print("No visible input found within 10s.")

        except Exception as e:
            print(f"Debug failed: {e}")
            await page.screenshot(path="d:/item/ProSourcing/niche_debug_fail.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_niche_page())
