import asyncio
import os
from playwright.async_api import async_playwright

async def relogin():
    # Remove old auth
    if os.path.exists("d:/item/ProSourcing/auth.json"):
        os.remove("d:/item/ProSourcing/auth.json")
        
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("https://app.algatop.kz/auth/login", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        await page.fill('input[type="email"], input[placeholder*="Email"]', '642712783@qq.com')
        await page.fill('input[type="password"]', 'xxyy0210..')
        
        # Press login
        await page.click('button[type="submit"]')
        
        # Wait for navigation
        await page.wait_for_timeout(5000)
        
        # Save state
        await context.storage_state(path="d:/item/ProSourcing/auth.json")
        print("Saved new auth.json")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(relogin())
