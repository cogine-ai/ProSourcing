
import re
from core.final_pipeline import supabase as sb

def test_full_logic():
    top_id = '01466'
    res = sb.table("categories").select("*").eq("category_id", top_id).execute()
    top_cat = res.data[0]
    category_name = top_cat['category_name']
    
    # 2. Extract RU name
    m = re.search(r'^(.*?)(?:\s*\(.*\))?$', category_name)
    ru_name = m.group(1).strip() if m else category_name
    print(f"RU Name: '{ru_name}'")

    # 3. Get all cats (limited for test)
    all_cats = []
    page_size = 1000
    for i in range(5):
        res = sb.table("categories").select("*").range(i * page_size, (i + 1) * page_size - 1).execute()
        all_cats.extend(res.data)
        if len(res.data) < page_size: break
    
    p_map = {}
    for cat in all_cats:
        pid = cat.get("parent_category_id")
        if pid not in p_map: p_map[pid] = []
        p_map[pid].append(cat)
    
    # 4. Find root
    root_id = top_id
    for cat in all_cats:
        if cat['category_name'] == ru_name and cat['category_id'] != top_id:
            root_id = cat['category_id']
            break
    print(f"Mapped root_id: {root_id}")

    # 5. Build leaves
    all_leaves = []
    def find_leaves_in_memory(p_id):
        children = p_map.get(p_id, [])
        for cat in children:
            if cat["is_has_subcategory"] == 0:
                all_leaves.append(cat)
            else:
                find_leaves_in_memory(cat["category_id"])

    find_leaves_in_memory(root_id)
    print(f"Found {len(all_leaves)} leaves.")
    if all_leaves:
        print(f"First leaf: {all_leaves[0]['category_name']}")

if __name__ == "__main__":
    test_full_logic()
