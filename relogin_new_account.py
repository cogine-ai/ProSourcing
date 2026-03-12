import asyncio
import json
import os
from playwright.async_api import async_playwright

# 哥，这是您的新凭据
USERNAME = "crab314@163.com"
PASSWORD = "Qq372655590."  # 包含小数点

async def login_and_save_auth():
    async with async_playwright() as p:
        user_data_dir = r"C:\AlgatopRPA_ChromeData"
        port = 9222
        import socket
        import subprocess
        def is_port_in_use(p):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('127.0.0.1', p)) == 0

        if not is_port_in_use(port):
            print("检测到 9222 端口未被占用，尝试自动启动 Chrome...")
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            if not os.path.exists(chrome_path):
                chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            user_data_dir = r"C:\AlgatopRPA_ChromeData"
            subprocess.Popen([chrome_path, f"--remote-debugging-port={port}", f"--user-data-dir={user_data_dir}"])
            await asyncio.sleep(5)

        print("正在连接到本地 Chrome...")
        browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        context = browser.contexts[0]
        page = await context.new_page()

        print(f"正在清理旧的凭据并访问 Algatop 登录页面...")
        try:
            await context.clear_cookies()
            await page.goto("https://app.algatop.kz/login", wait_until="domcontentloaded", timeout=60000)
            # 等待一会看是否跳转
            await asyncio.sleep(2)
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
        
        print(f"✅ 新账号凭据已成功同步至 {auth_path} 及持久化目录")
        await context.close()

if __name__ == "__main__":
    asyncio.run(login_and_save_auth())
