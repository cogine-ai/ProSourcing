import json
from supabase import create_client, Client

SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_supabase():
    print("Connecting to Supabase...")
    try:
        res = supabase.table("global_category_dict").select("*").limit(5).execute()
        print("Data sample from global_category_dict:")
        print(json.dumps(res.data, indent=2, ensure_ascii=False))
        
        if res.data:
            print("\nColumns found:", list(res.data[0].keys()))
    except Exception as e:
        print("Error accessing table:", e)

if __name__ == "__main__":
    check_supabase()
