import asyncio
import json
import os
import re
import sys
import io
from playwright.async_api import async_playwright

async def sync_algatop_tree():
    """
    全量抓取 Algatop 类目树。
    """
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("\n" + "="*60)
    print("🚀 Algatop 全量类目同步工具 (深度挖掘最终修正版)")
    print("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        storage_state = "d:/item/ProSourcing/auth.json"
        context_args = {}
        if os.path.exists(storage_state):
            context_args['storage_state'] = storage_state
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        try:
            target_url = "https://app.algatop.kz/niche"
            print(f"🌐 正在前往分类中心: {target_url}")
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
            
            if "/niche" not in page.url:
                print("⚠ 当前未在分类页，请手动操作进入 [Категории]...")
                for _ in range(60):
                    if "/niche" in page.url: break
                    await asyncio.sleep(1)

            print("✅ 确认就位，开始扫描...")

            last_count = 0
            for attempt in range(1, 60): # 增加轮次，深度可能很深
                # 核心逻辑：修复 el.click is not a function
                expand_stats = await page.evaluate('''() => {
                    let clicked = 0;
                    const rows = Array.from(document.querySelectorAll('tr'));
                    
                    rows.forEach(row => {
                        const link = row.querySelector('a[href*="/niche/category/"]');
                        if (!link) return;

                        // 找到行内所有可能的图标/按钮
                        const potentials = Array.from(row.querySelectorAll('svg, i, .v-icon, button, [role="button"]'));
                        
                        for (const el of potentials) {
                            try {
                                const style = window.getComputedStyle(el);
                                const rect = el.getBoundingClientRect();
                                
                                // 必须可见且是 pointer
                                if (rect.width === 0 || rect.height === 0 || style.display === 'none' || style.cursor !== 'pointer') continue;
                                
                                // 检查旋转状态 (已展开的箭头通常旋转 90度)
                                const transform = style.transform || style.webkitTransform || "";
                                if (transform.includes('matrix') && !transform.includes('1, 0, 0, 1')) continue;
                                
                                // 检查属性
                                if (el.getAttribute('aria-expanded') === 'true') continue;

                                // 确保在文字左边 (通常箭头在左边)
                                const linkRect = link.getBoundingClientRect();
                                if (rect.left < linkRect.left) {
                                    // 【修复点】：使用更稳妥的点击方式
                                    if (typeof el.click === 'function') {
                                        el.click();
                                        clicked++;
                                    } else {
                                        // 针对 SVG 或其他没有 .click() 的元素
                                        const ev = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });
                                        el.dispatchEvent(ev);
                                        clicked++;
                                    }
                                }
                            } catch(e) { /* 忽略单个元素点击失败 */ }
                        }
                    });
                    return clicked;
                }''')

                # 获取当前 Mapping 数量，修复 regex 警告
                current_mapping = await page.evaluate(r'''() => {
                    const links = Array.from(document.querySelectorAll('a[href*="/niche/category/"]'));
                    const map = {};
                    links.forEach(l => {
                        // 使用双反斜杠或原始字符串处理正则
                        const m = l.href.match(/\/category\/(\d+)/);
                        if (m && l.innerText.trim()) {
                            map[l.innerText.trim()] = m[1];
                        }
                    });
                    return map;
                }''')
                
                count = len(current_mapping)
                print(f"👉 [轮次 {attempt}] 触发点击: {expand_stats} | 当前已捕获类目: {count}")

                if expand_stats == 0 and count == last_count:
                    # 如果这轮没点着新的，且总数没变，多等一会儿
                    print("  ⏳ 尝试深度探测加载中...")
                    await asyncio.sleep(5)
                    # 再确认一次
                    final_check = await page.locator('a[href*="/niche/category/"]').count()
                    if final_check == count:
                        print("✨ 扫描完毕：所有分支已展开。")
                        break
                
                last_count = count
                await asyncio.sleep(2)

            # 保存结果
            print("\n💾 正在保存...")
            output_path = "d:/item/ProSourcing/output/algatop_id_mapping.json"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(current_mapping, f, ensure_ascii=False, indent=2)
            
            await context.storage_state(path=storage_state)
            
            print("\n" + "#"*50)
            print(f"🎉 同步成功！共捕获 {len(current_mapping)} 个有效 ID。")
            print("#"*50)
            
            print("\n哥，看到这个数涨到几千就说明全了。")
            print("请按 [ENTER] 回车键退出程序。")
            input()

        except Exception as e:
            print(f"❌ 出错: {e}")
            input("按回车键退出...")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(sync_algatop_tree())
