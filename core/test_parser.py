import os
import sys
import requests
import re
from bs4 import BeautifulSoup

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
    "Обувь": "00791",
    "Товары для дома и дачи": "00240",
    "Подарки, товары для праздников": "02605",
    "Канцелярские товары": "02062",
    "Товары для животных": "01466",
    "Продукты питания": "01793"
}

def heavy_parse():
    # 使用之前保存的 debug HTML 进行离线测试，确保逻辑正确后再上线
    file_path = "kaspi_debug.html"
    if not os.path.exists(file_path):
        print("❌ 找不到调试文件")
        return

    print(f"📖 正在深度解析 {file_path}...")
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    results = []
    
    # 查找所有 a 标签，Kaspi 的类目通常是链接
    links = soup.find_all('a')
    
    # 终极正则表达式：
    # 匹配模式：[名称] ... ( [带数字和空格的字符串] )
    # 示例："Одежда ( 1 939 803 )"
    regex = re.compile(r'\(\s*([\d\s]+)\s*\)')

    seen_ids = set()
    for link in links:
        text = link.get_text(strip=True)
        if not text: continue
        
        match = regex.search(text)
        if match:
            # 提取名称部分（去掉括号及其内容）
            name_part = text[:match.start()].strip()
            # 提取数字并去掉内嵌空格
            qty_str = match.group(1).replace(" ", "").replace("\xa0", "")
            
            if qty_str.isdigit():
                qty = int(qty_str)
                # 对齐映射
                for official_name, cat_id in CATEGORY_MAPPING.items():
                    # 这里用 startswith 因为 text 可能包含子类目，但一级类目通常在最前面
                    if official_name == name_part or name_part.startswith(official_name):
                        if cat_id not in seen_ids:
                            results.append({
                                "name": official_name,
                                "qty": qty,
                                "id": cat_id
                            })
                            seen_ids.add(cat_id)
                            break
    
    print(f"✅ 解析完成，找到 {len(results)} 个核心分类：")
    for r in results:
        print(f"  - {r['name']}: {r['qty']:,} (ID: {r['id']})")
    
    return results

if __name__ == "__main__":
    heavy_parse()
