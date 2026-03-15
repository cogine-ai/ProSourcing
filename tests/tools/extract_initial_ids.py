import re
import json
import os

html_path = "d:/item/ProSourcing/debug_niche.html"
if not os.path.exists(html_path):
    print(f"HTML file not found: {html_path}")
    exit(1)

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# 匹配模式：<a ... href="/niche/category/(\d+)" ...>(.*?)</a>
# 注意：HTML 中可能有嵌套标签，我们尽量匹配外层文本
pattern = r'href="/niche/category/(\d+)"[^>]*>(.*?)</a>'
matches = re.finditer(pattern, content, re.DOTALL)

mapping = {}
for match in matches:
    cat_id = match.group(1)
    # 清理文本，移除 HTML 标签
    raw_text = match.group(2)
    clean_text = re.sub(r'<[^>]+>', '', raw_text).strip()
    if clean_text and cat_id:
        mapping[clean_text] = cat_id

print(f"提取到 {len(mapping)} 个初始分类:")
for name, cid in list(mapping.items())[:25]:
    print(f"  {name}: {cid}")

output_path = "d:/item/ProSourcing/output/top_level_ids.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2)

print(f"已保存至 {output_path}")
