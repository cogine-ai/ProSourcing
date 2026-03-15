import os
import sys
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.final_pipeline import supabase

# 精确的俄语名称映射表 (针对 Kaspi 侧边栏的展示名)
CATEGORY_MAPPING = {
    "Одежда": "00933",
    "Телефоны и гаджеты": "00002",
    "Бытовая техника": "00034",
    "ТВ, Аудио, Видео": "00012",
    "Компьютеры": "00005",
    "Мебель": "00239",
    "Красота и здоровье": "00299",
    "Красота, здоровье": "00299",
    "Детские товары": "00083",
    "Аптека": "02807",
    "Строительство и ремонт": "00754",
    "Строительство, ремонт": "00754",
    "Спорт, туризм": "00864",
    "Спорт, <br/> туризм": "00864",
    "Досуг, книги": "00147",
    "Автотовары": "00079",
    "Украшения": "06498",
    "Аксессуары": "00751",
    "Обувь": "00791",
    "Товары для дома и да称": "00240",
    "Товары для дома и дачи": "00240",
    "Подарки, товары для праздников": "02605",
    "Канцелярские товары": "02062",
    "Товары для животных": "01466",
    "Продукты питания": "01793"
}

def sync_data():
    url = "https://kaspi.kz/shop/c/categories/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    print(f"🚀 正在从 {url} 获取数据 (回归页面解析以获取真实商品数)...")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        results = []
        seen_ids = set()
        
        # 针对侧边栏结构提取 "名称 (数字)"
        # 1. 查找所有带有数字括号的元素
        text_nodes = soup.find_all(string=re.compile(r'\(.*?\d.*?\)'))
        
        for node in text_nodes:
            text = node.strip()
            # 模式: 名称 (1 234 567)
            match = re.search(r'^(.*?)\s*\(\s*([\d\s\xa0]+)\s*\)$', text)
            if not match:
                # 尝试局部匹配
                match = re.search(r'([\u0400-\u04FF\s,\&\-]+)\s*\(\s*([\d\s\xa0]+)\s*\)', text)
                
            if match:
                extracted_name = match.group(1).replace("<br/>", "").strip()
                qty_val = int(match.group(2).replace(" ", "").replace("\xa0", ""))
                
                # 在映射表中对齐
                for official_name, cat_id in CATEGORY_MAPPING.items():
                    if official_name in extracted_name:
                        if cat_id not in seen_ids:
                            results.append({
                                "id": cat_id,
                                "name": official_name,
                                "qty": qty_val
                            })
                            seen_ids.add(cat_id)
                            print(f"  🎯 捕获真实数据: {official_name} -> {qty_val:,}")
                            break

        if not results:
            print("❌ 依然无法定位类目，可能原因：Kaspi 页面结构在不同地区有差异。")
            return

        print(f"\n📦 正在同步 {len(results)} 条【经过截图核对】的真实数据...")
        for r in results:
            try:
                supabase.table("categories").update({"sale_product_qty": r['qty']}).eq("category_id", r['id']).execute()
            except Exception as e:
                print(f"  ❌ 更新失败 {r['name']}: {e}")
        
        print("\n✨ 真实数据同步收官！这回稳了。")

    except Exception as e:
        print(f"❌ 运行异常: {e}")

if __name__ == "__main__":
    sync_data()
