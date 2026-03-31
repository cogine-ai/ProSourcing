
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = "https://furwnoxzsddkytimxtma.supabase.co"
key = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
print(f"URL being used: {url}")
print(f"Key being used: {key[:10]}...")
supabase = create_client(url, key)

def check_duplicates():
    # Fetch all records
    all_cats = []
    page_size = 1000
    for i in range(10):
        res = supabase.table('global_category_dict').select('*').range(i * page_size, (i + 1) * page_size - 1).execute()
        all_cats.extend(res.data)
        if len(res.data) < page_size: break
    
    print(f"Total categories fetched: {len(all_cats)}")
    
    # Check for duplicate algatop_id
    id_to_nodes = {}
    for cat in all_cats:
        aid = cat.get('algatop_id')
        if not aid: continue
        if aid not in id_to_nodes:
            id_to_nodes[aid] = []
        id_to_nodes[aid].append(cat)
    
    duplicates = {aid: nodes for aid, nodes in id_to_nodes.items() if len(nodes) > 1}
    
    if not duplicates:
        print("No duplicate algatop_id found.")
        return

    print(f"Found {len(duplicates)} duplicate algatop_ids.")
    for aid, nodes in list(duplicates.items())[:10]: # Show first 10
        print(f"\nAlgatop ID: {aid}")
        for n in nodes:
            print(f"  - Kaspi ID: {n['kaspi_id']}, Name CN: {n['name_cn']}, Name RU: {n['name_ru']}")

if __name__ == "__main__":
    check_duplicates()
