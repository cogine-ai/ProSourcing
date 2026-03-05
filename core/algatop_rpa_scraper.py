import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

class AlgatopRPAScraper:
    def __init__(self, port=9222):
        self.port = port
        self.browser = None
        self.context = None
        self.page = None
        self.captured_data = {
            "categories": [],
            "niche_stats": None,
            "products": [],
            "trend": []
        }

    async def connect(self):
        """连接到已经打开的 9222 端口 Chrome"""
        print(f"正在尝试连接到本地 Chrome (端口: {self.port})...")
        self.pw = await async_playwright().start()
        try:
            self.browser = await self.pw.chromium.connect_over_cdp(f"http://localhost:{self.port}")
            self.context = self.browser.contexts[0]
            self.page = self.context.pages[0]
            print(f"✅ 已成功接管浏览器窗口: {await self.page.title()}")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}. 请确保已运行 launch_rpa_chrome.py 并开启了调试端口。")
            return False

    async def setup_listeners(self):
        """设置 API 流量监听器"""
        async def handle_response(response):
            try:
                url = response.url
                # 1. 监听一级分类列表
                if "categoryListStatistic" in url:
                    data = await response.json()
                    if data.get("success"):
                        self.captured_data["categories"] = data["data"]
                        print(f"  [API] 捕获到 {len(data['data'])} 条一级分类数据")

                # 2. 监听最小品类聚合数据
                elif "categoryStatistic" in url and "categoryCode" in url:
                    data = await response.json()
                    if data.get("success"):
                        self.captured_data["niche_stats"] = data["data"]["statistic"][0]
                        print(f"  [API] 捕获到品类聚合数据: {self.captured_data['niche_stats'].get('category_name')}")

                # 3. 监听商品列表 (前8页)
                elif "niche/product" in url:
                    data = await response.json()
                    if data.get("success"):
                        lines = data["data"]["products"]["lines"]
                        self.captured_data["products"].extend(lines)
                        print(f"  [API] 捕获到 {len(lines)} 条商品数据 (总计: {len(self.captured_data['products'])})")

                # 4. 监听趋势图数据
                elif "categoryStatisticLine" in url:
                    data = await response.json()
                    if data.get("success"):
                        self.captured_data["trend"] = data["data"]
                        print(f"  [API] 捕获到趋势图数据 ({len(data['data'])} 个月)")

            except Exception:
                pass # 忽略非 JSON 或无关响应

        self.page.on("response", handle_response)
        print("💡 API 流量监听已开启。哥，你现在可以在浏览器里随便点点，数据会自动同步。")

    async def human_click(self, selector):
        """精准物理模拟点击"""
        try:
            btn = self.page.locator(selector).first
            if await btn.is_visible():
                box = await btn.bounding_box()
                if box:
                    # 模拟真人移动鼠标到中心点
                    await self.page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    await asyncio.sleep(0.5)
                    await self.page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    return True
            return False
        except Exception as e:
            print(f"点击失败: {e}")
            return False

    async def scrape_niche_products(self, pages=8):
        """模拟真人翻页抓取前 8 页商品数据"""
        print(f"正在模拟真人翻页抓取前 {pages} 页...")
        self.captured_data["products"] = [] # 重置
        
        for p in range(1, pages + 1):
            print(f"  -> 正在处理第 {p} 页...")
            # 这里的 selector 需要根据 Algatop 实际结构调整。
            # 通常翻页按钮有 .pagination-next 或者类似。
            # 哥，如果翻页按钮点不动，你可以手动点，脚本后台会自动截获 API 数据。
            if p > 1:
                # 尝试寻找“下一页”按钮并模拟点击
                # 这里我们用最保险的选择器：包含“>”或者“Next”的按钮
                next_btn = self.page.locator('button:has-text(">"), .next, [aria-label*="Next"]').last
                if await next_btn.is_visible():
                    await self.human_click('button:has-text(">"), .next, [aria-label*="Next"]')
                    await asyncio.sleep(3) # 模拟真人等待加载
                else:
                    print(f"  [Warning] 未找到第 {p} 页的翻页按钮，请哥手动点一下。")
                    await asyncio.sleep(5) 
            else:
                await asyncio.sleep(2) # 第一页等待一下即可
                
        print(f"✅ 翻页采集结束。共提取 {len(self.captured_data['products'])} 条商品条目。")

    async def save_to_file(self, filename="rpa_output.json"):
        """保存捕获到的全量数据"""
        path = os.path.join("d:/item/ProSourcing/output", filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.captured_data, f, ensure_ascii=False, indent=2)
        print(f"💾 数据已实时保存至: {path}")

async def main():
    rpa = AlgatopRPAScraper()
    connected = await rpa.connect()
    if connected:
        await rpa.setup_listeners()
        
        # 这里是一个交互式的等待演示
        print("\n--- 任务开始 ---")
        print("哥，现在你可以去浏览器里点开你想分析的品类列表。")
        print("当你准备好抓取前 8 页商品数据时，请回到这里按任意键继续...")
        
        # 模拟等待用户操作
        await asyncio.get_event_loop().run_in_executor(None, input, "按回车键开始自动翻页抓取前 8 页商品...")
        
        await rpa.scrape_niche_products(8)
        await rpa.save_to_file()
        
    await rpa.pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
