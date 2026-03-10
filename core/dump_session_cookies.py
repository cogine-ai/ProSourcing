import asyncio
import json
import os
from playwright.async_api import async_playwright

async def dump_cookies():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        
        if not os.path.exists(storage_state):
            print("auth.json not found")
            return

        context = await browser.new_context(storage_state=storage_state)
        cookies = await context.cookies()
        
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        print("\n--- Session Cookies ---")
        print(cookie_str)
        
        # 保存到临时文件供其它脚本使用
        with open("d:/item/ProSourcing/output/cookies_raw.txt", "w") as f:
            f.write(cookie_str)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(dump_cookies())
