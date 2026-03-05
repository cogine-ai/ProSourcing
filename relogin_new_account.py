import asyncio
import json
import os
from playwright.async_api import async_playwright

# 哥，这是您的新凭据
USERNAME = "xie@cogine.ai"
PASSWORD = "Qq372655590."  # 包含小数点

async def login_and_save_auth():
    async with async_playwright() as p:
        # 使用真实的浏览器头
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"正在访问 Algatop 登录页面...")
        try:
            await page.goto("https://app.algatop.kz/login", wait_until="domcontentloaded", timeout=60000)
        except:
            print("访问超时，但我们将继续尝试查找元素...")

        print(f"正在输入凭据 (User: {USERNAME})...")
        await page.wait_for_selector('input[type="email"]', timeout=20000)
        await page.fill('input[type="email"]', USERNAME)
        await page.fill('input[type="password"]', PASSWORD)
        
        print("正在提交登录...")
        await page.click('button[type="submit"]')

        # 等待登录成功跳转
        print("等待跳转至主页...")
        try:
            # 只要看到 niche 就算成功
            await page.wait_for_url("**/niche/**", timeout=45000)
            print("登录成功！")
        except:
            print("未能自动检测到跳转，尝试在当前页面提取凭据...")
            await asyncio.sleep(5)

        # 导出最新的 auth 信息
        storage = await context.storage_state()
        auth_path = "d:/item/ProSourcing/auth.json"
        with open(auth_path, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 新账号凭据已成功同步至 {auth_path}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(login_and_save_auth())
