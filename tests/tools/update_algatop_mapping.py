import json
import os
import sys

# 添加项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.final_pipeline import supabase as sb

def update_database_mapping():
    mapping_path = "d:/item/ProSourcing/output/algatop_id_mapping.json"
    if not os.path.exists(mapping_path):
        print(f"Mapping file not found at {mapping_path}")
        return

    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    if not mapping:
        print("Mapping is empty, nothing to update.")
        return

    print(f"Starting database sync for {len(mapping)} categories...")
    
    # 获取数据库中现有的类目名，用于匹配
    try:
        response = sb.table("global_category_dict").select("name_ru").execute()
        db_categories = {row['name_ru'] for row in response.data}
        
        updates = []
        for name, aid in mapping.items():
            if name in db_categories:
                updates.append({
                    "name_ru": name,
                    "algatop_id": aid
                })
        
        if updates:
            print(f"Updating {len(updates)} matching categories individually...")
            success_count = 0
            for up in updates:
                try:
                    sb.table("global_category_dict").update({"algatop_id": up["algatop_id"]}).eq("name_ru", up["name_ru"]).execute()
                    success_count += 1
                except:
                    pass
            print(f"🎉 Database successfully updated with {success_count} Algatop IDs.")
        else:
            print("No matching category names found in database.")
    except Exception as e:
        print(f"Error during database update: {e}")

if __name__ == "__main__":
    update_database_mapping()
