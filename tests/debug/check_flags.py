
from core.final_pipeline import supabase as sb

def count_leaves():
    res = sb.table("categories").select("count", count="exact").eq("is_leaf", True).execute()
    print(f"Nodes with is_leaf=true: {res.count}")
    
    res = sb.table("categories").select("count", count="exact").eq("is_leaf", False).execute()
    print(f"Nodes with is_leaf=false: {res.count}")

if __name__ == "__main__":
    count_leaves()
