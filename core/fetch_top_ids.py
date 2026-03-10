import sys
import os
import json

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.final_pipeline import supabase as sb

def fetch_top_level_ids():
    print("Fetching top-level categories from global_category_dict...")
    # Fetch categories where parent_algatop_id is null and algatop_id exists
    res = sb.table("global_category_dict").select("category_name, algatop_id").is_("parent_algatop_id", "null").neq("algatop_id", None).execute()
    data = res.data
    
    if not data:
        print("No top level IDs found with parent_algatop_id IS NULL.")
        # Try another way: maybe is_top_level=True
        res = sb.table("global_category_dict").select("category_name, algatop_id").eq("is_top_level", True).neq("algatop_id", None).execute()
        data = res.data

    if not data:
        # One last try: just get some IDs to start with if nothing is marked as top level
        res = sb.table("global_category_dict").select("category_name, algatop_id").neq("algatop_id", None).limit(21).execute()
        data = res.data

    print(f"Found {len(data)} potential seed categories:")
    mapping = {}
    for item in data:
        name = item['category_name']
        aid = item['algatop_id']
        mapping[name] = aid
        print(f"  {name}: {aid}")
        
    output_path = "d:/item/ProSourcing/output/top_level_ids.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    fetch_top_level_ids()
