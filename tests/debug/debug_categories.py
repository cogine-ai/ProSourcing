
from core.final_pipeline import supabase as sb
import re

def test_category_debug():
    # 1. 检查是否存在一级分类
    res = sb.table("categories").select("*").eq("is_top_level", True).limit(5).execute()
    if not res.data:
        print("Error: No top level categories found in database.")
        return
    
    for top_cat in res.data:
        top_id = top_cat['category_id']
        category_name = top_cat['category_name']
        print(f"\n--- Checking Top Category: {category_name} (ID: {top_id}) ---")
        
        # 2. 模拟 server.py 中的正则逻辑
        m = re.search(r'^(.*?)(?:\s*\(.*\))?$', category_name)
        ru_name = m.group(1).strip() if m else category_name
        print(f"Extracted RU Name: '{ru_name}'")

        # 3. 检查是否有子类目的 parent_category_id 对应这个 top_id
        children_res = sb.table("categories").select("*").eq("parent_category_id", top_id).limit(5).execute()
        print(f"Direct children count (by ID): {len(children_res.data)}")
        
        # 4. 模拟 server.py 中的 root_id 转换逻辑
        # 它在找名称相同但 ID 不同的节点作为真正根节点
        other_nodes = sb.table("categories").select("*").eq("category_name", ru_name).execute()
        root_candidates = [cat['category_id'] for cat in other_nodes.data]
        print(f"Nodes found with name '{ru_name}': {root_candidates}")
        
        # 5. 统计该分类下的总类目数
        total = sb.table("categories").select("count", count="exact").execute()
        print(f"Total categories in table: {total.count}")

if __name__ == "__main__":
    test_category_debug()
