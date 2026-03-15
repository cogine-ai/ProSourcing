import asyncio
import json
import os
import io
import sys
from playwright.async_api import async_playwright

async def extract_via_dom_expansion():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("\n" + "="*60)
    print("🚀 Algatop 全量类目同步工具 (DOM 递归版)")
    print("="*60)
    print("💡 正在通过模拟点击直接在页面内展开类目树...")

    async with async_playwright() as p:
        # 使用有界面的 Chromium 以增加成功率 (本地运行)
        browser = await p.chromium.launch(headless=True)
        storage_state = "d:/item/ProSourcing/auth.json"
        
        if not os.path.exists(storage_state):
            print("❌ 错误：检测不到 auth.json")
            await browser.close()
            return

        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        
        print("🔗 正在加载 Niche 页面...")
        try:
            await page.goto("https://app.algatop.kz/niche", wait_until="commit", timeout=60000)
            # 等待表格加载出来（这是真正的开始标志）
            await page.wait_for_selector(".ant-table-row", timeout=30000)
        except Exception as e:
            print(f"  ⚠️ 页面完全加载超时，但我们将尝试直接操作 DOM: {e}")
        
        await asyncio.sleep(5)

        # 核心逻辑：递归点击展开箭头
        print("🖱️ 开始递归展开分类树 (这可能需要 1-2 分钟)...")
        
        # 注入扩展脚本
        expand_js = '''async () => {
            let clickedCount = 0;
            async function expandAll() {
                // 查找所有未展开的箭头 (通常是某些特定的 class 或带有特定图标的元素)
                // 观察发现点击后箭头会旋转，或者子元素会加载
                // 我们寻找那些具有展开潜力的节点
                const toggles = Array.from(document.querySelectorAll('i.ant-table-row-expand-icon:not(.ant-table-row-expand-icon-expanded):not(.ant-table-row-expand-icon-spaced)'));
                
                if (toggles.length === 0) return false;
                
                for (let t of toggles) {
                    t.click();
                    clickedCount++;
                    // 稍微等一下加载数据
                    await new Promise(r => setTimeout(r, 600)); 
                }
                return true;
            }

            let hasMore = true;
            while (hasMore) {
                hasMore = await expandAll();
                // 如果发现没有更多可以点的了，或者点了一圈还没变化，就停
            }
            return clickedCount;
        }'''

        try:
            total_clicks = await page.evaluate(expand_js)
            print(f"✅ 展开完成，共执行点击: {total_clicks}")
        except Exception as e:
            print(f"⚠️ 展开过程中出现非致命错误: {e}")

        # 提取数据
        print("📊 正在提取当前页面的全量 ID 映射...")
        
        mapping = await page.evaluate('''() => {
            const links = Array.from(document.querySelectorAll('a[href*="/niche/category/"]'));
            const res = {};
            links.forEach(l => {
                const match = l.href.match(/\/category\/(\d+)/);
                const text = l.innerText.trim();
                if (match && text) {
                    res[text] = match[1];
                }
            });
            return res;
        }''')
        
        # 保存结果
        output_path = "d:/item/ProSourcing/output/algatop_id_mapping.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
            
        print("\n" + "#"*60)
        print(f"🎉 同步完成！")
        print(f"🔢 共捕获类目数量: {len(mapping)}")
        print(f"💾 映射结果已更新至: {output_path}")
        print("#"*60)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_via_dom_expansion())
