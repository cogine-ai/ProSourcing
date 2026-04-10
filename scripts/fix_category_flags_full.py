
import sys
from core.final_pipeline import supabase as sb

def fix_all_categories():
    print("Full Fix Start...")
    
    # 1. First Pass: Reset everything to 1 just to be standard (if needed, but 1 is usually default)
    
    # 2. Identify parents across ALL 3425 categories
    # PostgREST has 1000 limit, must paginate
    all_cats = []
    for i in range(5):
        res = sb.table("categories").select("category_id, parent_category_id").range(i*1000, (i+1)*1000-1).execute()
        all_cats.extend(res.data)
        if len(res.data) < 1000: break
    
    print(f"Total entries loaded: {len(all_cats)}")
    
    parent_ids = set()
    for cat in all_cats:
        pid = cat.get('parent_category_id')
        if pid:
            parent_ids.add(pid)
    
    leaf_ids = [c['category_id'] for c in all_cats if c['category_id'] not in parent_ids]
    parent_to_fix_ids = [c['category_id'] for c in all_cats if c['category_id'] in parent_ids]

    print(f"Total Leaves to set 0: {len(leaf_ids)}")
    print(f"Total Parents to set 1: {len(parent_to_fix_ids)}")

    # Update leaves
    batch_size = 100
    l_count = 0
    for i in range(0, len(leaf_ids), batch_size):
        batch = leaf_ids[i:i + batch_size]
        sb.table("categories").update({"is_has_subcategory": 0}).in_("category_id", batch).execute()
        l_count += len(batch)
        if l_count % 500 == 0: print(f"Leaves done: {l_count}")

    # Update parents
    p_count = 0
    for i in range(0, len(parent_to_fix_ids), batch_size):
        batch = parent_to_fix_ids[i:i + batch_size]
        sb.table("categories").update({"is_has_subcategory": 1}).in_("category_id", batch).execute()
        p_count += len(batch)
    
    print(f"Finished. Updated {l_count} leaves to '0' and {p_count} parents to '1'.")

if __name__ == "__main__":
    fix_all_categories()
