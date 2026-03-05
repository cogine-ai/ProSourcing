
from core.final_pipeline import supabase as sb

def check_link():
    # 1. 查找子类目中常见的 parent_id
    res = sb.table("categories").select("parent_category_id").neq("parent_category_id", "").limit(200).execute()
    parents_in_children = set(c['parent_category_id'] for c in res.data if c.get('parent_category_id'))
    print(f"Subcategories point to these parents: {list(parents_in_children)[:10]}")

    # 2. 检查这些 parent_id 是否作为 category_id 存在
    if parents_in_children:
        target = list(parents_in_children)[0]
        exists = sb.table("categories").select("*").eq("category_id", target).execute()
        if exists.data:
            print(f"Parent '{target}' exists as a category record.")
        else:
            print(f"Parent '{target}' DOES NOT exist as a category record (Orphaned sub-tree).")

    # 3. 检查有没有名称重合的情况
    # 假设 'Pet goods' 是英文 ID，看看有没有名称类似的
    res = sb.table("categories").select("*").ilike("category_name", "%животн%").execute()
    print("\nCategories related to 'pets' (俄文):")
    for c in res.data:
        print(f"ID: {c['category_id']}, Parent: {c['parent_category_id']}, Name: {c['category_name']}, Top: {c['is_top_level']}")

if __name__ == "__main__":
    check_link()
