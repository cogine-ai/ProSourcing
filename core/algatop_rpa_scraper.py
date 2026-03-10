import asyncio
import json
import os
import re
import sys
import random
import time
import math
from urllib.parse import quote
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

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
        self.total_api_pages = 0 # 自动嗅探到的总页数
        self.current_api_url_template = None # 捕获到的产品列表 API 模板
        self.user = os.getenv("ALGATOP_USER")
        self.password = os.getenv("ALGATOP_PASS")

        # 随机 User-Agent 池
        self.ua_pool = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ]

    async def connect(self):
        """连接到已经打开的 9222 端口 Chrome，并注入 Stealth"""
        print(f"[CONNECT] 正在尝试连接到本地 Chrome (端口: {self.port})...")
        self.pw = await async_playwright().start()
        try:
            # 明确使用 127.0.0.1 避免 IPv6 导致的 localhost 链接问题
            self.browser = await self.pw.chromium.connect_over_cdp(f"http://127.0.0.1:{self.port}")
            self.context = self.browser.contexts[0]
            # 创建一个新页面，而不是复用可能不稳定的第一个页面
            self.page = await self.context.new_page()
            
            # --- Browser Pool / Stealth 增强 ---
            await Stealth().apply_stealth_async(self.page) 
            # 覆盖一些关键指纹
            await self.page.emulate_media(color_scheme="dark")
            print(f"[SUCCESS] 已成功接管浏览器窗口: {await self.page.title()}")
            return True
        except Exception as e:
            print(f"[ERROR] 连接失败: {e}")
            return False

    async def human_delay(self, min_ms=800, max_ms=2500):
        """更随机的真人延迟"""
        delay = random.uniform(min_ms, max_ms) / 1000.0
        # 增加一点长停顿概率 (5%)
        if random.random() < 0.05:
            delay += random.uniform(2, 5)
        await asyncio.sleep(delay)

    def _get_bezier_points(self, start, end, steps=20):
        """生成贝塞尔曲线路径点，模拟真人鼠标移动"""
        points = []
        # 随机控制点
        ctrl_x = random.randint(min(start[0], end[0]), max(start[0], end[0]))
        ctrl_y = random.randint(min(start[1], end[1]), max(start[1], end[1]))
        
        for i in range(steps + 1):
            t = i / steps
            # 二次贝塞尔曲线公式: (1-t)^2*P0 + 2t(1-t)*P1 + t^2*P2
            x = int((1-t)**2 * start[0] + 2*t*(1-t)*ctrl_x + t**2 * end[0])
            y = int((1-t)**2 * start[1] + 2*t*(1-t)*ctrl_y + t**2 * end[1])
            points.append((x, y))
        return points

    async def human_move_to(self, target_x, target_y):
        """模拟真人平滑移动鼠标"""
        curr_pos = {'x': 0, 'y': 0} # 暂时假定从原点开始，Playwright 内部会处理
        # 实际操作中可以使用上一次点击的位置
        steps = random.randint(15, 30)
        # 这里简单起见从当前位置移动到目标位置
        # Playwright 的 mouse.move 支持 steps 属性，但贝塞尔更真实
        points = self._get_bezier_points((random.randint(0, 500), random.randint(0, 500)), (target_x, target_y), steps)
        for x, y in points:
            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.005, 0.015))

    async def human_click(self, selector):
        """高强度真人模拟点击"""
        try:
            element = self.page.locator(selector).first
            await element.scroll_into_view_if_needed()
            box = await element.bounding_box()
            if box:
                # 目标点包含随机偏移
                target_x = int(box['x'] + box['width'] * random.uniform(0.2, 0.8))
                target_y = int(box['y'] + box['height'] * random.uniform(0.2, 0.8))
                
                await self.human_move_to(target_x, target_y)
                await self.human_delay(100, 300)
                await self.page.mouse.down()
                await asyncio.sleep(random.uniform(0.05, 0.15)) # 模拟按下时长
                await self.page.mouse.up()
                return True
            return False
        except Exception as e:
            print(f"[CLICK ERROR] {e}")
            return False

    async def human_type(self, selector, text):
        """模拟真人逐字输入并包含偶尔的退格重输"""
        element = self.page.locator(selector).first
        await self.human_click(selector)
        await self.human_delay(200, 500)
        
        for i, char in enumerate(text):
            await self.page.keyboard.type(char, delay=random.randint(80, 200))
            # 2% 概率输入错位并退格
            if random.random() < 0.02 and i > 0:
                await self.page.keyboard.type(random.choice("abcdefghijklmnopqrstuvwxyz"), delay=100)
                await asyncio.sleep(0.3)
                await self.page.keyboard.press("Backspace")
                await asyncio.sleep(0.2)

    async def perform_login(self):
        """执行自动登录流程"""
        print("[LOGIN] 检测到需要登录，正在执行自动登录流程...")
        if not self.user or not self.password:
            raise Exception("Missing credentials in .env")
        
        # 使用更通用的选择器
        await self.human_type('input[type="text"], input[name="email"], .v-text-field input', self.user)
        await self.human_delay(500, 1000)
        await self.human_type('input[type="password"]', self.password)
        await self.human_delay(800, 1500)
        
        # 点击登录按钮
        await self.human_click('button[type="submit"], .v-btn--is-elevated:has-text("Войти")')
        
        try:
            await self.page.wait_for_url("**/niche/**", timeout=20000)
            print("[SUCCESS] 登录成功！")
        except:
            print("[WARNING] 登录跳转超时，可能需要处理验证码。")

    async def setup_listeners(self):
        """设置 API 监听器 (Page 级别增加鲁棒性)"""
        async def handle_response(response):
            try:
                url = response.url
                # 监控所有 API
                if "algatop.kz/api" in url:
                    status = response.status
                    print(f"  [API DEBUG] URL: {url} | Status: {status}")
                    
                    # 匹配类目大盘数据 (提取 URL 中的真实时间范围)
                    if "categoryStatistic" in url and "categoryStatisticLine" not in url:
                        try:
                            # 从 URL 提取日期参数 (例如 startDate=20260129&endDate=20260228)
                            from urllib.parse import urlparse, parse_qs
                            parsed_url = urlparse(url)
                            query_params = parse_qs(parsed_url.query)
                            
                            s_date = query_params.get("startDate", [None])[0]
                            e_date = query_params.get("endDate", [None])[0]
                            
                            data = await response.json()
                            if data.get("success") and "data" in data:
                                stats = data["data"].get("statistic", [])
                                if stats:
                                    self.captured_data["niche_stats"] = stats[0]
                                    # 将从 URL 提取的真实起止日期合并到 stats 中回传
                                    if s_date: self.captured_data["niche_stats"]["startDate"] = s_date
                                    if e_date: self.captured_data["niche_stats"]["endDate"] = e_date
                                    print(f"[API SUCCESS] 捕获指标({s_date}-{e_date}): {self.captured_data['niche_stats'].get('category_name')}")
                        except Exception as e:
                            print(f"[API WARN] 提取指标数据失败: {e}")

                    elif "niche/product" in url:
                        try:
                            # 记录 API 模板，用于后续上帝模式翻页
                            if "page=1" in url and not self.current_api_url_template:
                                self.current_api_url_template = url.replace("page=1", "page={page}")
                                print(f"[API INFO] 已锁定产品列表 API 模板: {self.current_api_url_template}")

                            data = await response.json()
                            if data.get("success"):
                                products_data = data.get("data", {}).get("products", {})
                                items = products_data.get("lines", [])
                                
                                # 嗅探总页数
                                summary = products_data.get("summary", [])
                                if summary and "page_count" in summary[0]:
                                    self.total_api_pages = int(summary[0]["page_count"])
                                    print(f"[API INFO] 嗅探到总页数: {self.total_api_pages}")

                                if items:
                                    # 简单去重逻辑，防止 API 重复捕获
                                    existing_ids = {p.get('product_code') for p in self.captured_data["products"]}
                                    new_items = [p for p in items if p.get('product_code') not in existing_ids]
                                    self.captured_data["products"].extend(new_items)
                                    print(f"[API SUCCESS] 捕获商品: {len(new_items)} 条 (总计: {len(self.captured_data['products'])})")
                        except Exception as e:
                            print(f"[API ERROR] 处理产品接口失败: {e}")

                    elif "categoryStatisticLine" in url:
                        try:
                            data = await response.json()
                            if data.get("success"):
                                self.captured_data["trend"] = data["data"]
                                print(f"[API SUCCESS] 捕获趋势图数据: {len(data['data'])} 条")
                        except: pass
            except:
                pass

        self.page.on("response", handle_response)
        print("[LISTENER] 全路径 API 流量监听已开启。")

    async def navigate_to_category(self, category_code):
        """高拟人直跳导航 (增加重试机制以应对网络波动)"""
        if not category_code or str(category_code).lower() == "test_category":
            print(f"[FATAL ERROR] 接收到非法类目参数: '{category_code}'")
            return False

        print(f"[NAV] 正在导航至类目详情: {category_code}...")
        encoded_code = quote(str(category_code))
        target_url = f"https://app.algatop.kz/niche/category/{encoded_code}"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 延长超时到 60s，并使用更宽松的 commit 阶段
                await self.page.goto(target_url, wait_until="commit", timeout=60000)
                await self.human_delay(3000, 6000)
                break
            except Exception as e:
                print(f"[NAV RETRY] 第 {attempt + 1} 次尝试失败: {e}")
                if attempt == max_retries - 1:
                    print("[FATAL] 导航多次重试均失败。")
                    return False
                await asyncio.sleep(5)

        # 2. 如果跳转到登录页，执行登录后再次导航
        if "login" in self.page.url:
            await self.perform_login()
            await self.page.goto(target_url, wait_until="commit", timeout=60000)
            await self.human_delay(3000, 5000)
        
        # 3. 确认捕获到了数据 (关键修复：死磕趋势和指标数据)
        print("[CHECK] 正在等待核心分析数据捕获...")
        timeout = 45  # 哥，再多给点时间，趋势图加载有时很慢
        while timeout > 0:
            # 趋势数据必须拿到，指标数据也必须拿到
            if self.captured_data["niche_stats"] and self.captured_data["trend"]:
                print(f"[SUCCESS] 核心数据已全部捕获 (耗时: {45 - timeout}s)")
                return True
            
            # 如果指标拿到了但趋势没拿到，尝试模拟滚动一下，触发图表加载
            if self.captured_data["niche_stats"] and not self.captured_data["trend"] and timeout < 35:
                print("[RETRY] 指标已就位，但趋势图消失。尝试模拟滚动以触发懒加载...")
                await self.page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(2)
                
            await asyncio.sleep(1)
            timeout -= 1
        
        if not self.captured_data["trend"]:
            print("[WARNING] 趋势数据捕获最终由于超时失败。尝试最后一次强力滚动...")
            # 暴力向下滚动 10 次，每次 300 像素，确保触发懒加载
            for _ in range(5):
                await self.page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1.5)
                if self.captured_data["trend"]:
                    print("[SUCCESS] 最后时刻补救成功，捕获到趋势数据！")
                    return True
            
        return self.captured_data["niche_stats"] is not None

    async def fetch_extra_pages(self, max_pages=None):
        """上帝模式：直接调用 API 接口获取剩余分页，无视 UI 状态"""
        if not self.current_api_url_template or self.total_api_pages <= 1:
            print("[INFO] 无需执行 API 驱动翻页（无模板或只有一页）")
            return

        total_to_fetch = self.total_api_pages
        if max_pages:
            total_to_fetch = min(self.total_api_pages, max_pages)

        print(f"[GOD MODE] 开始 API 驱动翻页，计划抓取至第 {total_to_fetch} 页...")

        for p in range(2, total_to_fetch + 1):
            fetch_url = self.current_api_url_template.format(page=p)
            print(f"[GOD MODE] 正在通过浏览器 Fetch 抓取第 {p}/{total_to_fetch} 页...")
            
            try:
                # 使用 page.evaluate 在浏览器上下文中直接 Fetch，绕过复杂的点击逻辑
                # 这样可以利用浏览器已有的 Session 和校验 Header
                script = f'''async () => {{
                    const res = await fetch("{fetch_url}", {{
                        headers: {{ "top-l": "2s3dfnfRgn43PkgmPolqre#" }}
                    }});
                    return await res.json();
                }}'''
                result = await self.page.evaluate(script)
                
                if result.get("success"):
                    items = result.get("data", {}).get("products", {}).get("lines", [])
                    if items:
                        existing_ids = {item.get('product_code') for item in self.captured_data["products"]}
                        new_items = [item for item in items if item.get('product_code') not in existing_ids]
                        self.captured_data["products"].extend(new_items)
                        print(f"[GOD MODE SUCCESS] 第 {p} 页抓取成功，新增 {len(new_items)} 条商品")
                    else:
                        print(f"[GOD MODE WARN] 第 {p} 页接口返回空数据")
                else:
                    print(f"[GOD MODE FAILED] 第 {p} 页接口请求失败: {result.get('message')}")
                
                # 适当延迟，防止请求过快触发风控
                await asyncio.sleep(random.uniform(1.5, 3.0))
                
            except Exception as e:
                print(f"[GOD MODE ERROR] 抓取第 {p} 页时发生异常: {e}")

    async def navigate_to_next_page(self):
        """模拟真人翻页 (作为备用方案)"""
        # 增加对俄语的支持
        next_btn_selector = 'button.v-pagination__navigation[aria-label="Next page"], button.v-pagination__navigation[aria-label="Следующая страница"], button.v-pagination__navigation i.mdi-chevron-right'
        try:
            # 滚动到底部寻找翻页键
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.human_delay(1000, 2000)
            
            if await self.page.locator(next_btn_selector).first.is_visible():
                print("[NAV] 正在点击下一页...")
                await self.human_click(next_btn_selector)
                await self.human_delay(3000, 5000) # 等待数据加载
                return True
            else:
                print("[INFO] 未找到下一页按钮，可能已到末尾。")
                return False
        except Exception as e:
            print(f"[ERROR] 翻页失败: {e}")
            return False

    async def save_results(self, task_id="default"):
        """保存采集结果"""
        filename = f"rpa_output_{task_id}.json"
        path = os.path.join("d:/item/ProSourcing/output", filename)
        # 确保目录存在
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.captured_data, f, ensure_ascii=False, indent=2)
        print(f"[SAVE] 采集完成，累计商品: {len(self.captured_data['products'])} 条，数据已落盘: {path}")

async def main():
    # 默认使用 04456 (儿童交通) 进行多页测试
    category = sys.argv[1] if len(sys.argv) > 1 else "04456"
    task_id = sys.argv[2] if len(sys.argv) > 2 else "manual_test"
    max_pages = 8
    
    scraper = AlgatopRPAScraper()
    if await scraper.connect():
        try:
            await scraper.setup_listeners()
            if await scraper.navigate_to_category(category):
                print(f"[START] 开始采集前 {max_pages} 页数据...")
                
                # 1. 优先使用 API 驱动翻页 (上帝模式)
                await scraper.fetch_extra_pages(max_pages=max_pages)

                # 2. 如果 API 没拉到数据，才尝试传统的 UI 翻页 (兜底)
                if len(scraper.captured_data["products"]) < 20 and max_pages > 1:
                    print("[INFO] API 翻页未获取到足够数据，切换至 UI 兜底翻页模式...")
                    current_page = 1
                    while current_page < max_pages:
                        if await scraper.navigate_to_next_page():
                            current_page += 1
                        else:
                            break
                
                # 最后保存
                await scraper.save_results(task_id)
                return True
            else:
                print("[ERROR] 类目数据加载失败")
                return False
        finally:
            if hasattr(scraper, 'pw') and scraper.pw:
                await scraper.pw.stop()

if __name__ == "__main__":
    if not asyncio.run(main()):
        sys.exit(1)
