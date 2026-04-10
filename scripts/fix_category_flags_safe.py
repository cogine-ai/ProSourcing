
import sys
from core.final_pipeline import supabase as sb

def fix_leaf_nodes():
    print("Starting fix_leaf_nodes...")
    
    # 1. Fetch all categories
    res = sb.table("categories").select("category_id, parent_category_id").execute()
    all_cats = res.data
    print(f"Total categories: {len(all_cats)}")
    
    # 2. Identify parents
    parent_ids = set()
    for cat in all_cats:
        pid = cat.get('parent_category_id')
        if pid:
            parent_ids.add(pid)
    
    # 3. Identify leaves (those that are not parents)
    leaf_ids = []
    for cat in all_cats:
        cat_id = cat['category_id']
        if cat_id not in parent_ids:
            leaf_ids.append(cat_id)
            
    print(f"Identified leaf nodes: {len(leaf_ids)}")
    
    # 4. Batch update is_has_subcategory = 0
    batch_size = 50
    success_count = 0
    
    for i in range(0, len(leaf_ids), batch_size):
        batch = leaf_ids[i:i + batch_size]
        try:
            sb.table("categories").update({"is_has_subcategory": 0}).in_("category_id", batch).execute()
            success_count += len(batch)
            if success_count % 500 == 0:
                print(f"Updated {success_count} nodes...")
        except Exception as e:
            print(f"Batch failed: {str(e)}")
            
    # 5. Reset parents to 1 (just in case)
    print("Ensuring parents are marked with is_has_subcategory=1...")
    p_success = 0
    p_list = list(parent_ids)
    for i in range(0, len(p_list), batch_size):
        batch = p_list[i:i + batch_size]
        try:
            sb.table("categories").update({"is_has_subcategory": 1}).in_("category_id", batch).execute()
            p_success += len(batch)
        except Exception as e:
            print(f"Parent batch failed: {str(e)}")

    print(f"Final Success: {success_count} leaves, {p_success} parents updated.")

if __name__ == "__main__":
    fix_leaf_nodes()
