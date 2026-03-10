import asyncio
import json
import os
import sys
import datetime
from playwright.async_api import async_playwright

async def run_local_sync():
    """
    哥，这个脚本是为你本地运行设计的。
    它会启动一个可见的浏览器，直接在你面前操作分类树并抓取全量 ID。
    """
    print("\n" + "="*60)
    print("🚀 Algatop 本地同步桥接工具")
    print("="*60)
    print("💡 正在为你启动本地浏览器进行数据抓取...")

    async with async_playwright() as p:
        # 本地运行建议 headless=False 让你能看到进度
        browser = await p.chromium.launch(headless=False)
        storage_state = "d:/item/ProSourcing/auth.json"
        
        if not os.path.exists(storage_state):
            print("❌ 错误：检测不到 auth.json，请先运行 relogin_new_account.py")
            await browser.close()
            return

        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        
        print("🔗 正在打开 Niche 页面...")
        await page.goto("https://app.algatop.kz/niche", wait_until="load", timeout=90000)
        
        print("⌛ 等待页面初始化...")
        await page.wait_for_selector(".ant-table-row", timeout=30000)
        await asyncio.sleep(2)

        # 注入递归抓取逻辑
        print("🖱️ 正在执行自动化点击与扫描...")
        # 这是一个复杂的混合逻辑：先尝试 API，如果 API 被墙，则回退到 DOM 展开
        mapping = await page.evaluate('''async () => {
            const results = {};
            const topL = "2s3dfnfRgn43PkgmPolqre#";
            
            async function fetchLevel(cid) {
                const url = `/api/v1/niche/categoryListStatistic?startDate=20260207&endDate=20260309&categoryId=${cid}`;
                try {
                    const res = await fetch(url, { headers: { "top-l": topL } });
                    const json = await res.json();
                    if (json && json.data) {
                        for (let item of json.data) {
                            const name = item.category_name || item.categoryName;
                            const id = item.category_id || item.categoryId;
                            if (name && id) {
                                results[name] = id;
                                // 递归探测
                                if (item.is_has_subcategory !== false) {
                                    await fetchLevel(id);
                                }
                            }
                        }
                    }
                } catch (e) {}
            }

            // 从根节点开始
            await fetchLevel("");
            return results;
        }''')

        if not mapping:
            print("⚠️ API 探测失败，尝试从当前 DOM 直接提取...")
            mapping = await page.evaluate('''() => {
                const res = {};
                document.querySelectorAll('a[href*="/niche/category/"]').forEach(l => {
                    const id = l.href.match(/\\/category\\/(\\d+)/)?.[1];
                    const name = l.innerText.trim();
                    if (id && name) res[name] = id;
                });
                return res;
            }''')

        # 保存结果
        output_path = "d:/item/ProSourcing/output/algatop_id_mapping.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
            
        print("\n" + "#"*60)
        print(f"🎉 本地同步完成！")
        print(f"🔢 共捕获类目数量: {len(mapping)}")
        print(f"💾 结果已存入: {output_path}")
        print("#"*60)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_local_sync())
