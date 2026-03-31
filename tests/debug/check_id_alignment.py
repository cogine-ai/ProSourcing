from supabase import create_client
import json
import re

SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def cleanup_name(name):
    # 去掉括号及其内容，如 "Пульсоксиметры (脉搏血氧计)" -> "Пульсоксиметры"
    return re.sub(r'\(.*?\)', '', name).strip()

def check_id_mapping():
    print("Fetching categories from Supabase...")
    all_cats = []
    for i in range(5):
        res = supabase.table("categories").select("category_id, category_name").range(i*1000, (i+1)*1000-1).execute()
        if not res.data: break
        all_cats.extend(res.data)
    
    print(f"Total categories in DB: {len(all_cats)}")

    mapping_path = "d:/item/ProSourcing/output/algatop_id_mapping.json"
    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    print(f"Total numeric IDs in mapping file: {len(mapping)}")

    matched = 0
    missing = []
    for cat in all_cats:
        cname = cat['category_name']
        pure_name = cleanup_name(cname)
        
        # 尝试直接匹配
        if pure_name in mapping:
            matched += 1
        else:
            missing.append(cname)

    print(f"\n--- Mapping Result ---")
    print(f"Matched by Name: {matched} / {len(all_cats)} ({matched/len(all_cats)*100:.1f}%)")
    print(f"Missing Mapping: {len(all_cats) - matched}")
    
    if missing:
        print("\nSample missing categories (first 10):")
        for m in missing[:10]:
            print(f"  - {m}")

if __name__ == "__main__":
    check_id_mapping()
