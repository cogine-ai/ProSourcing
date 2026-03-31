import json
from supabase import create_client, Client

SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_categories():
    print("Checking 'categories' table...")
    res = supabase.table("categories").select("*").limit(5).execute()
    print(json.dumps(res.data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    check_categories()
