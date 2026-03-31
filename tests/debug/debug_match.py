import re
from core.final_pipeline import supabase as sb

def clean_name(n):
    # 清理名称用于匹配：转小写，去空格，去标点，去掉括号内容
    n = re.sub(r'[\(\/].*$', '', n) # 去掉 (中文)
    n = re.sub(r'[^\w\s]', '', n) # 去标点
    return "".join(n.lower().split()).replace('и', '') # 额外去掉 'и' 以应对 'Красота и здоровье' vs 'Красота, здоровье'

# 模拟 server.py 中的逻辑
res = sb.table("categories").select("*").eq("is_top_level", True).order("monthly_sales", desc=True).execute()
tops = res.data

all_cats = []
page_size = 1000
for i in range(10): 
    r = sb.table("categories").select("category_id, category_name, parent_category_id, is_has_subcategory").range(i * page_size, (i + 1) * page_size - 1).execute()
    all_cats.extend(r.data)
    if len(r.data) < page_size: break

print(f"Total cats in memory: {len(all_cats)}")

results = []
for top in tops:
    orig_name = top['category_name']
    cleaned_top = clean_name(orig_name)
    
    match_id = None
    match_name = None
    for c in all_cats:
        cleaned_c = clean_name(c['category_name'])
        if cleaned_c == cleaned_top and c['category_id'] != top['category_id']:
            match_id = c['category_id']
            match_name = c['category_name']
            break
    
    results.append({
        "orig": orig_name,
        "cleaned": cleaned_top,
        "match_id": match_id,
        "match_name": match_name
    })

import json
print(json.dumps(results, indent=2, ensure_ascii=False))
