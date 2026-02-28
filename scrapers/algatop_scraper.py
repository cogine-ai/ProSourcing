import os
import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

class BaseScraper:
    def __init__(self, storage_state_path="auth.json"):
        self.storage_state_path = storage_state_path
        self.user = os.getenv("ALGATOP_USER")
        self.password = os.getenv("ALGATOP_PASS")

    async def init_browser(self, headless=True):
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=headless)
        
        # 强制设置更写实的 User-Agent
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        if self.storage_state_path and os.path.exists(self.storage_state_path):
            self.context = await self.browser.new_context(
                storage_state=self.storage_state_path,
                user_agent=user_agent
            )
        else:
            self.context = await self.browser.new_context(user_agent=user_agent)
        
        self.page = await self.context.new_page()
        self.page.set_default_timeout(60000)

    async def save_state(self):
        if self.storage_state_path:
            await self.context.storage_state(path=self.storage_state_path)

    async def close(self):
        if hasattr(self, 'browser'):
            await self.browser.close()
        if hasattr(self, 'pw'):
            await self.pw.stop()

class AlgatopScraper(BaseScraper):
    async def login(self):
        """
        尝试执行登录，如果已有 session 则跳过，如果超时则尝试直接进入业务页
        """
        print("Checking if already logged in by accessing /niche...")
        try:
            # 使用 commit 策略，只要服务器响应了 Headers 就进去
            await self.page.goto("https://app.algatop.kz/niche", wait_until="commit", timeout=90000)
            await asyncio.sleep(5) # 给点时间渲染
            if "auth/login" not in self.page.url:
                print("Direct access to /niche successful (Already logged in).")
                return
        except Exception as e:
            print(f"Direct access failed or timed out: {e}, trying login page...")

        login_url = "https://app.algatop.kz/auth/login/mail"
        try:
            await self.page.goto(login_url, wait_until="domcontentloaded", timeout=90000)
            
            # 兼容性寻找 Email
            email_input = self.page.locator('input[name="email"], input[type="email"]').first
            if await email_input.count() > 0:
                print("Filling credentials...")
                await email_input.fill(self.user)
                await self.page.locator('input[name="password"], input[type="password"]').first.fill(self.password)
                
                await self.page.keyboard.press("Enter")
                print("Waiting for post-login navigation...")
                try:
                    await self.page.wait_for_url("**/niche**", timeout=60000)
                    print("Login successful!")
                    await self.save_state()
                except:
                    print("Login redirect timed out, but proceeding...")
            else:
                print("Login form not found.")
                await self.page.screenshot(path="d:/item/ProSourcing/login_missing.png")
        except Exception as e:
            print(f"Login attempt failed: {e}")

    async def search_niche_by_sku(self, sku):
        print(f"Searching niche for SKU: {sku}")
        try:
            # 尝试直接去页面，不等待 networkidle
            await self.page.goto("https://app.algatop.kz/niche", wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(10) # 强制等待框架加载
            
            # 如果加载不出来，打印出当前可见的 text 看看
            body_text = await self.page.inner_text('body')
            if "Ниши" not in body_text and "Niche" not in body_text:
                print("Page might be empty or loading. Body snippet:", body_text[:200])
            
            # 使用更暴力的方式寻找搜索框：只要是第一个 input
            search_input = self.page.locator('input').first
            await search_input.click()
            await search_input.fill(str(sku))
            await self.page.keyboard.press("Enter")
            
            print("Searching... (wait 10s)")
            await asyncio.sleep(10)
            
            # 寻找结果表格
            # 通常会有 <a> 标签指向详情
            links = self.page.locator('table a[href*="/niche/"]')
            if await links.count() > 0:
                link = links.first
                name = await link.inner_text()
                href = await link.get_attribute('href')
                full_url = f"https://app.algatop.kz{href}" if href.startswith('/') else href
                print(f"Found Niche: {name.strip()} -> {full_url}")
                return {"name": name.strip(), "url": full_url}
            else:
                print("No niche results in table.")
                await self.page.screenshot(path="d:/item/ProSourcing/no_niche.png")
                return None
        except Exception as e:
            print(f"Search error: {e}")
            await self.page.screenshot(path="d:/item/ProSourcing/search_error.png")
            return None

    async def get_niche_stats(self, niche_url):
        print(f"Fetching stats from {niche_url}")
        try:
            await self.page.goto(niche_url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(10) # 等待数据加载
            
            stats = {}
            # 更加通用的数据提取：寻找包含数字和货币符号的容器
            # 这里的定位需要根据实际页面（俄语）调整
            # 常见标签：Продажи (Sales), Выручка (GMV)
            
            all_text = await self.page.inner_text('body')
            
            import re
            # 尝试正则匹配 销量
            # 格式可能是 "Продажи 1,234" 或者类似
            # 我们先打印出来，手动分析一次
            print("Page content length:", len(all_text))
            
            # 为演示目的，我们尝试几个可能的 selector
            # 假设数据在特定的卡片里
            cards = self.page.locator('.card, .stats-card, [class*="Stat"]')
            count = await cards.count()
            print(f"Found {count} potential stat cards.")
            
            for i in range(count):
                txt = await cards.nth(i).inner_text()
                if "Продажи" in txt or "Sales" in txt:
                    stats['sales'] = txt.replace("\n", " ").strip()
                if "Выручка" in txt or "Revenue" in txt or "GMV" in txt:
                    stats['gmv'] = txt.replace("\n", " ").strip()
            
            print(f"Final Stats: {stats}")
            return stats
        except Exception as e:
            print(f"Stats extraction error: {e}")
            return {}

if __name__ == "__main__":
    async def debug():
        scraper = AlgatopScraper()
        await scraper.init_browser(headless=True)
        await scraper.login()
        # 切换为关键词搜索，因为 SKU 可能没被索引
        keyword = "коврик для йоги"
        print(f"DEBUG: Searching by keyword: {keyword}")
        res = await scraper.search_niche_by_sku(keyword) # 方法名虽然叫 by_sku，但逻辑是通用的 input
        if res:
            data = await scraper.get_niche_stats(res['url'])
            print(f"FINAL DATA OBTAINED: {data}")
        else:
            print("COULD NOT FIND NICHE BY KEYWORD.")
        await scraper.close()
    asyncio.run(debug())
