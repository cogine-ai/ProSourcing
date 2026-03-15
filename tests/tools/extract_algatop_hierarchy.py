
import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

async def run_extraction():
    async with async_playwright() as p:
        # Connect to the existing browser (port 9222)
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            print("Connected to browser on 9222")
        except Exception as e:
            print(f"Failed to connect to browser on 9222: {e}")
            return

        context = browser.contexts[0]
        # Find the Niche page or open a new one
        page = None
        for p_obj in context.pages:
            if "algatop.kz/niche" in p_obj.url:
                page = p_obj
                break
        
        if not page:
            print("Niche page not found, opening new one...")
            page = await context.new_page()
            await page.goto("https://app.algatop.kz/niche", wait_until="commit")
        else:
            print(f"Using existing page: {page.url}")

        # JS script to recursively fetch categories
        extraction_js = '''
        async () => {
            const startDate = "20260211";
            const endDate = "20260311";
            const headers = {
                "top-l": "2s3dfnfRgn43PkgmPolqre#",
                "referer": "https://app.algatop.kz/niche"
            };

            const rootIds = ["00002", "00005", "00012", "00034", "00079", "00083", "00147", "00239", "00240", "00299", "00751", "00754", "00791", "00864", "00933", "01466", "01793", "02062", "02605", "02807", "06498"];
            const tree = [];

            async function fetchChildren(parentId, level) {
                const url = `/api/v1/niche/categoryListStatistic?startDate=${startDate}&endDate=${endDate}&categoryId=${parentId}`;
                console.log(`Fetching children for ${parentId} at level ${level}...`);
                try {
                    const res = await fetch(url, { headers });
                    if (!res.ok) return [];
                    const json = await res.json();
                    if (!json.success || !json.data) return [];
                    
                    const children = [];
                    for (const item of json.data) {
                        const child = {
                            id: item.category_id || item.categoryId,
                            name: item.category_name || item.categoryName,
                            parent_id: parentId,
                            level: level + 1,
                            children: []
                        };
                        // Only recurse if we think it has children. 
                        // Note: The API usually returns subcategories. If it's a leaf, it might return empty or null.
                        // We'll try to fetch anyway, but with a limit to avoid infinite loops
                        if (level < 10) {
                            child.children = await fetchChildren(child.id, level + 1);
                        }
                        children.push(child);
                    }
                    return children;
                } catch (e) {
                    console.error(`Error fetching ${parentId}:`, e);
                    return [];
                }
            }

            // For roots, we need to handle them specially because categoryId=0 might not work for all.
            // But we already have the root names/ids from the subagent.
            const roots = [
                {"name": "Телефоны и гаджеты", "id": "00002"},
                {"name": "Компьютеры", "id": "00005"},
                {"name": "ТВ, Аудио, Видео", "id": "00012"},
                {"name": "Бытовая техника", "id": "00034"},
                {"name": "Автотовары", "id": "00079"},
                {"name": "Детские товары", "id": "00083"},
                {"name": "Досуг, книги", "id": "00147"},
                {"name": "Мебель", "id": "00239"},
                {"name": "Товары для дома и дачи", "id": "00240"},
                {"name": "Красота и здоровье", "id": "00299"},
                {"name": "Аксессуары", "id": "00751"},
                {"name": "Строительство, ремонт", "id": "00754"},
                {"name": "Обувь", "id": "00791"},
                {"name": "Спорт, туризм", "id": "00864"},
                {"name": "Одежда", "id": "00933"},
                {"name": "Товары для животных", "id": "01466"},
                {"name": "Продукты питания", "id": "01793"},
                {"name": "Канцелярские товары", "id": "02062"},
                {"name": "Подарки, товары для праздников", "id": "02605"},
                {"name": "Аптека", "id": "02807"},
                {"name": "Украшения", "id": "06498"}
            ];

            for (const root of roots) {
                const node = {
                    id: root.id,
                    name: root.name,
                    parent_id: null,
                    level: 0,
                    children: await fetchChildren(root.id, 0)
                };
                tree.push(node);
            }

            return tree;
        }
        '''

        print("Starting extraction in browser context...")
        full_tree = await page.evaluate(extraction_js)
        
        output_path = "d:/item/ProSourcing/output/algatop_full_tree.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(full_tree, f, ensure_ascii=False, indent=2)
        
        print(f"Extraction complete! Saved to {output_path}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_extraction())
