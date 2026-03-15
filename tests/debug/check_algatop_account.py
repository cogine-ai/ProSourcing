import asyncio
import os
import io
import sys
import json
from playwright.async_api import async_playwright

async def check_account():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        
        context_args = {}
        if os.path.exists(storage_state):
            context_args['storage_state'] = storage_state
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        print("Accessing Algatop to check account info...")
        try:
            await page.goto("https://app.algatop.kz/", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
            
            # Try to find user email/name in the UI
            # Looking at common places like profile menus or settings
            user_info = await page.evaluate('''() => {
                const bodyText = document.body.innerText;
                const emailMatch = bodyText.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g);
                return {
                    url: window.location.href,
                    emails: emailMatch ? Array.from(new Set(emailMatch)) : [],
                    title: document.title
                };
            }''')
            
            print(f"Current URL: {user_info['url']}")
            print(f"Found emails in page: {user_info['emails']}")
            
            # Take a crop of the top-right corner where profile info usually is
            await page.screenshot(path="d:/item/ProSourcing/debug_profile.png", clip={'x': 800, 'y': 0, 'width': 400, 'height': 200})
            print("Saved profile screenshot to debug_profile.png")
            
        except Exception as e:
            print(f"Failed to check account: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_account())
