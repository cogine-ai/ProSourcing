"""
fetch_top_category_stats.py
采用和 algatop_rpa_scraper.py 完全一致的 CDP 接管 + 浏览器内 Fetch 方案，
直接复用浏览器已有的 session/cookie，最稳定、不被风控。
"""
import asyncio
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timedelta

from playwright.async_api import async_playwright

# 复用项目已有的 supabase 客户端
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from final_pipeline import supabase


async def main():
    # ── 1. 从数据库拉出 21 个一级大类 ──
    res = supabase.table("algatop_categories_master").select("*").eq("level", 1).execute()
    top_categories = res.data

    if not top_categories:
        print("未在 algatop_categories_master 中找到 level=1 的大类！")
        return

    # 拉取已经成功入库且有真实数据（过滤掉全为0的默认记录）的大类统计数据，避免重复抓取浪费额度
    stats_res = supabase.table("algatop_top_category_stats").select("algatop_id, sales_qty").execute()
    existing_ids = {item["algatop_id"] for item in stats_res.data if item.get("sales_qty", 0) > 0} if stats_res.data else set()


    print(f"找到了 {len(top_categories)} 个一级大类")

    # ── 2. 连接到 Chrome (127.0.0.1:9222) ──
    port = 9222

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
    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    except Exception as e:
        print(f"连接 Chrome 失败: {e}")
        print("请确保已打开带有 --remote-debugging-port=9222 并且登录了 Algatop 的 Chrome。")
        await pw.stop()
        return

    context = browser.contexts[0]

    # ── 3. 找到已打开的 algatop 页面（和 RPA 一样复用已有 tab） ──
    page = None
    for p in context.pages:
        if "algatop.kz" in p.url:
            page = p
            break

    if not page:
        print("未找到已打开的 algatop 页面，新建标签页...")
        page = await context.new_page()
        try:
            await page.goto("https://app.algatop.kz/niche", wait_until="commit", timeout=60000)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"导航失败: {e}")
            await pw.stop()
            return
    else:
        print(f"找到已打开的 algatop 页面: {page.url}")

    # ── 4. 构造日期区间 ──
    today = datetime.now()
    end_date_dt = today - timedelta(days=1)
    start_date_dt = end_date_dt - timedelta(days=30)
    start_date = start_date_dt.strftime("%Y%m%d")
    end_date = end_date_dt.strftime("%Y%m%d")
    print(f"抓取时间区间: {start_date} - {end_date}")

    # ── 5. 循环抓取，使用 page.evaluate(fetch(...)) —— 和 RPA 采集完全一样的方式 ──
    success_count = 0

    for cat in top_categories:
        code = cat["algatop_id"]
        name = cat.get("name_cn") or cat.get("name_ru") or code

        if code in existing_ids:
            print(f"已存在 [{code}] {name} 的数据，跳过...")
            success_count += 1 # 当作成功处理以维持统计准确性，或者不加也行，这里选择不增加抓取成功数，最后打印实际新抓取数量
            continue

        print(f"正在抓取 [{code}] {name} ...")

        api_url = f"https://app.algatop.kz/api/v1/niche/categoryStatistic?startDate={start_date}&endDate={end_date}&categoryCode={code}"

        # 核心：在浏览器上下文中执行 fetch，自动带上所有鉴权
        script = f'''async () => {{
            try {{
                const res = await fetch("{api_url}", {{
                    headers: {{ "top-l": "2s3dfnfRgn43PkgmPolqre#" }}
                }});
                return await res.json();
            }} catch(e) {{
                return {{ success: false, error: e.message }};
            }}
        }}'''

        try:
            result = await page.evaluate(script)
        except Exception as e:
            print(f"  -> page.evaluate 异常: {e}")
            continue

        if not result or not result.get("success"):
            err_msg = result.get("message") or result.get("error") or "未知错误"
            print(f"  -> 接口返回失败: {err_msg}")
            continue

        data = result.get("data", {})
        # 调试：当 statistic 为空时打印整个 data 结构
        access = data.get("access", {})
        stat_list = data.get("statistic", [])
        if not stat_list:
            print(f"  -> statistic 为空, data keys={list(data.keys())}, access={access}")
            continue

        stat = stat_list[0] if isinstance(stat_list, list) else stat_list

        payload = {
            "algatop_id": code,
            "sales_qty": stat.get("sale_qty", 0),
            "revenue": stat.get("sale_amount", 0),
            "product_count": stat.get("sale_product_qty", 0),
            "seller_count": stat.get("sale_merchant_qty", 0),
            "brand_count": stat.get("sale_brand_qty", 0),
            "updated_at": datetime.now().isoformat()
        }

        try:
            supabase.table("algatop_top_category_stats").upsert(payload).execute()
            success_count += 1
            print(f"  -> 入库成功: 销量={payload['sales_qty']}, 销售额={payload['revenue']}, 商品数={payload['product_count']}")
        except Exception as db_err:
            print(f"  -> 入库失败: {db_err}")

        await asyncio.sleep(1.5)  # 礼貌延迟

    print(f"\n抓取完成！成功入库 {success_count}/{len(top_categories)} 个一级大类数据。")
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
