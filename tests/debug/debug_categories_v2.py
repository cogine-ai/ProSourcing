
from core.final_pipeline import supabase as sb

def test_deep_lookup():
    # 找几个真实的 ID 看看结构
    res = sb.table("categories").select("*").limit(10).execute()
    print("--- Sample Categories ---")
    for cat in res.data:
        print(f"ID: {cat['category_id']}, Parent: {cat.get('parent_category_id')}, Name: {cat['category_name']}")

    # 看看父类 ID 的分布
    res = sb.table("categories").select("parent_category_id").limit(100).execute()
    parents = set(c.get('parent_category_id') for c in res.data if c.get('parent_category_id'))
    print(f"\nSample parent IDs: {list(parents)[:10]}")
    
    # 看看有没有 ID 是 02807 或类似格式的子类
    if parents:
        example_parent = list(parents)[0]
        res = sb.table("categories").select("*").eq("category_id", example_parent).execute()
        if res.data:
            print(f"\nExample Parent Node: {res.data[0]}")
        else:
            print(f"\nParent ID {example_parent} exists in children but NOT as its own record!")

if __name__ == "__main__":
    test_deep_lookup()
