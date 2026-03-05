
from core.final_pipeline import supabase as sb

def check_top_level():
    res = sb.table("categories").select("*").eq("is_top_level", True).execute()
    print(f"Top Level Count: {len(res.data)}")
    for c in res.data[:20]:
        print(f"ID: {c['category_id']}, Name: {c['category_name']}")

if __name__ == "__main__":
    check_top_level()
