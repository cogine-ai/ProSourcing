import os
import sys
import requests
import re
from bs4 import BeautifulSoup

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.final_pipeline import supabase

# 精确的俄语名称映射表
CATEGORY_MAPPING = {
    "Одежда": "00933",
    "Телефоны и гаджеты": "00002",
    "Бытовая техника": "00034",
    "ТВ, Аудио, Видео": "00012",
    "Компьютеры": "00005",
    "Мебель": "00239",
    "Красота и здоровье": "00299",
    "Детские товары": "00083",
    "Аптека": "02807",
    "Строительство и ремонт": "00754",
    "Спорт, туризм": "00864",
    "Досуг, книги": "00147",
    "Автотовары": "00079",
    "Украшения": "06498",
    "Аксессуары": "00751",
    "О布вь": "00791", # 改回俄语 Обувь
    "Товары для дома и дачи": "00240",
    "Подарки, товары для праздников": "02605",
    "Канцелярские товары": "02062",
    "Товары для животных": "01466",
    "Продукты питания": "01793"
}

# 修正映射表里的错别字（手动核对源码）
CATEGORY_MAPPING["Обувь"] = "00791"

def sync_data():
    url = "https://kaspi.kz/shop/c/categories/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    print(f"🚀 正在从 {url} 获取数据 (BS + RE 混合模式)...")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # 找到所有包含分类的链接
        links = soup.find_all('a')
        
        results = []
        seen_ids = set()
        
        # 预编译正则，匹配括号内的带空格数字
        qty_regex = re.compile(r'\(\s*([\d\s\xa0]+)\s*\)')

        for link in links:
            # get_text(strip=True) 会把 <a><span>名称</span><span>( 123 )</span></a> 平铺成 "名称( 123 )"
            full_text = link.get_text(strip=True)
            if not full_text: continue
            
            # 查找括号数字
            match = qty_regex.search(full_text)
            if match:
                # 剔除数字后的残余名字
                extracted_name = full_text[:match.start()].strip()
                qty_val = int(match.group(1).replace(" ", "").replace("\xa0", ""))
                
                # 排除那个“所有类别”的一千万大数
                if "Все категории" in extracted_name or qty_val > 10000000:
                    continue

                # 在映射表中匹配
                for official_name, cat_id in CATEGORY_MAPPING.items():
                    if official_name == extracted_name and cat_id not in seen_ids:
                        results.append({
                            "id": cat_id,
                            "name": official_name,
                            "qty": qty_val
                        })
                        seen_ids.add(cat_id)
                        print(f"  🎯 捕获: {official_name} -> {qty_val:,}")
                        break
        
        if not results:
            print("💡 警告：抓取失败，正在尝试暴力搜索模式...")
            # 如果上面那种方式失败，退回到在整段文本里找名字关键字
            for official_name, cat_id in CATEGORY_MAPPING.items():
                # 寻找包含该名字的 HTML 元素
                element = soup.find(string=re.compile(re.escape(official_name)))
                if element:
                    parent_text = element.parent.get_text(strip=True)
                    match = qty_regex.search(parent_text)
                    if match:
                        qty_val = int(match.group(1).replace(" ", "").replace("\xa0", ""))
                        if cat_id not in seen_ids:
                            results.append({"id": cat_id, "name": official_name, "qty": qty_val})
                            seen_ids.add(cat_id)
                            print(f"  🔥 暴力捕获: {official_name} -> {qty_val:,}")

        if not results:
            print("❌ 依然无果，建议检查 Kaspi 是否启用了强力反爬或结构大改。")
            return

        print(f"\n📦 正在同步 {len(results)} 条精准数据...")
        for r in results:
            try:
                supabase.table("categories").update({"sale_product_qty": r['qty']}).eq("category_id", r['id']).execute()
            except Exception as e:
                print(f"  ❌ 更新失败 {r['name']}: {e}")
        
        print("\n✨ 精准数据已写入数据库。")

    except Exception as e:
        print(f"❌ 运行异常: {e}")

if __name__ == "__main__":
    sync_data()
