
from core.final_pipeline import supabase as sb

def count_leaves():
    res = sb.table("categories").select("count", count="exact").eq("is_has_subcategory", 0).execute()
    print(f"Nodes with is_has_subcategory=0: {res.count}")
    
    res = sb.table("categories").select("count", count="exact").eq("is_has_subcategory", 1).execute()
    print(f"Nodes with is_has_subcategory=1: {res.count}")

if __name__ == "__main__":
    count_leaves()
