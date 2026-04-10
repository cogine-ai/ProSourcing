
import re
from core.final_pipeline import supabase as sb

def sync_leaf_counts_to_db():
    print("Starting sync_leaf_counts_to_db...")
    
    # 1. Fetch all top level categories (Algatop style)
    res = sb.table("categories").select("*").eq("is_top_level", True).execute()
    tops = res.data
    
    # 2. Fetch all categories to build tree in memory
    all_cats = []
    page_size = 1000
    for i in range(10):
        r = sb.table("categories").select("category_id, category_name, parent_category_id, is_has_subcategory").range(i * page_size, (i + 1) * page_size - 1).execute()
        all_cats.extend(r.data)
        if len(r.data) < page_size: break
        
    p_map = {}
    for cat in all_cats:
        pid = cat.get("parent_category_id")
        if pid not in p_map: p_map[pid] = []
        p_map[pid].append(cat)
        
    def count_leaves_recursive(p_id):
        count = 0
        children = p_map.get(p_id, [])
        for cat in children:
            if cat.get("is_has_subcategory") == 0:
                count += 1
            else:
                count += count_leaves_recursive(cat["category_id"])
        return count

    print(f"Processing {len(tops)} top categories...")
    for top in tops:
        # Get RU name to find Kaspi root ID
        m = re.search(r'^(.*?)(?:\s*\(.*\))?$', top['category_name'])
        ru_name = m.group(1).strip() if m else top['category_name']
        
        real_root_id = top['category_id']
        for c in all_cats:
            if c['category_name'] == ru_name and c['category_id'] != top['category_id']:
                real_root_id = c['category_id']
                break
        
        count = count_leaves_recursive(real_root_id)
        print(f"  - {top['category_name']}: {count} leaves")
        
        # Update DB
        sb.table("categories").update({"leaf_count": count}).eq("category_id", top['category_id']).execute()

    print("✅ Sync complete.")

if __name__ == "__main__":
    sync_leaf_counts_to_db()
