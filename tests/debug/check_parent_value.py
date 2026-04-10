
from core.final_pipeline import supabase as sb

def check_one():
    res = sb.table("categories").select("*").eq("category_id", "Livestock goods").execute()
    print(f"Livestock goods node: {res.data}")

if __name__ == "__main__":
    check_one()
