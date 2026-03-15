import re
import json
from core.final_pipeline import supabase as sb

def clean_name(n):
    n = re.sub(r'[\(\/].*$', '', n)
    n = re.sub(r'[^\w\s]', '', n)
    return "".join(n.lower().split()).replace('и', '')

# 拉取数据
res = sb.table("categories").select("*").eq("is_top_level", True).order("monthly_sales", desc=True).execute()
tops = res.data

all_cats = []
page_size = 1000
for i in range(10): 
    r = sb.table("categories").select("*").range(i * page_size, (i + 1) * page_size - 1).execute()
    all_cats.extend(r.data)
    if len(r.data) < page_size: break

p_map = {}
for cat in all_cats:
    pid = cat.get("parent_category_id")
    if pid not in p_map: p_map[pid] = []
    p_map[pid].append(cat)

def get_all_leaves(p_id):
    leaves = []
    children = p_map.get(p_id, [])
    for child in children:
        if child.get("is_has_subcategory") == 0:
            leaves.append(child)
        else:
            leaves.extend(get_all_leaves(child["category_id"]))
    return leaves

results = []
for top in tops:
    orig_name = top['category_name']
    cleaned_top = clean_name(orig_name)
    
    match_id = None
    for c in all_cats:
        cleaned_c = clean_name(c['category_name'])
        if cleaned_c == cleaned_top and c['category_id'] != top['category_id']:
            match_id = c['category_id']
            break
    
    leaves = []
    if match_id:
        leaves = get_all_leaves(match_id)
    
    results.append({
        "name": orig_name,
        "match_id": match_id,
        "leaf_count": len(leaves)
    })

print(json.dumps(results, indent=2, ensure_ascii=False))
