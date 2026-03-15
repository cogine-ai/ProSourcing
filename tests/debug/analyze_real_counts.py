import os
import re
from bs4 import BeautifulSoup

def analyze_offline():
    file_path = "kaspi_debug.html"
    if not os.path.exists(file_path):
        print("❌ 找不到调试文件")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    
    # 针对截图中的数据：所有类别 (12572994)
    # 我们找包含数字括号的文本
    print("🔍 正在从源码中扫描类目和数量...")
    
    # 查找所有文本节点，匹配 "名称 (数字)"
    # 比如 "Одежда (1 939 806)"
    text_pattern = re.compile(r'([\u0400-\u04FF\s,\d\-]+)\s*\(\s*([\d\s\xa0]+)\s*\)')
    
    found = []
    # 遍历所有 a 标签或 span 标签，它们通常包含类目名
    for tag in soup.find_all(['a', 'span', 'li']):
        content = tag.get_text(separator=" ", strip=True)
        if not content: continue
        
        # 排除掉太长的或者显然不是类目的
        if len(content) > 100: continue
        
        match = text_pattern.search(content)
        if match:
            name = match.group(1).strip()
            qty_raw = match.group(2).replace(" ", "").replace("\xa0", "").strip()
            if qty_raw.isdigit():
                qty = int(qty_raw)
                # 过滤掉一些干扰项
                if qty > 0:
                    found.append((name, qty))

    # 去重并排序
    unique_found = sorted(list(set(found)), key=lambda x: x[1], reverse=True)
    
    print("\n✅ 源码提取到的真实数据前 30 条：")
    for name, qty in unique_found:
        print(f"  - {name}: {qty:,}")

if __name__ == "__main__":
    analyze_offline()
