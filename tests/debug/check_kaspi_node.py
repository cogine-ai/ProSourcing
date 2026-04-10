
from core.final_pipeline import supabase as sb

def check_one():
    # 看看 Kaspi 风格的节点长什么样
    res = sb.table("categories").select("*").eq("category_id", "Pet goods").execute()
    print(f"Kaspi Item: {res.data}")

if __name__ == "__main__":
    check_one()
