from supabase import create_client, Client
import json

SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def verify_db():
    sku = "112769474"
    resp = supabase.table("products_raw_data").select("*").eq("sku", sku).execute()
    if resp.data:
        p = resp.data[0]
        print(f"SKU: {p['sku']}")
        print(f"Rating: {p.get('rating')}")
        print(f"Weight: {p.get('weight')}")
        print(f"Commission: {p.get('commission')}")
        print(f"Image URL: {p.get('image_url')[:50]}...")
        print(f"Category Total Sales: {p.get('category_total_sales')}")
    else:
        print("No data found for SKU")

if __name__ == "__main__":
    verify_db()
