import json
import os
from supabase import create_client, Client

SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_to_db():
    json_path = "d:/item/ProSourcing/output/algatop_master_final.json"
    print(f"Reading data from {json_path}...")
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"Total entries in JSON: {len(data)}")
    
    # 哥，JSON 里有些 ID 是重复的，我们按 ID 去重，保留最后一条
    unique_data = {}
    for item in data:
        unique_data[item['algatop_id']] = item
    
    unique_list = list(unique_data.values())
    print(f"Unique records after deduplication: {len(unique_list)}")
    
    batch_size = 100
    total_synced = 0
    
    print("Starting batch upsert...")
    for i in range(0, len(unique_list), batch_size):
        batch = unique_list[i : i + batch_size]
        try:
            # 这里的字段名必须与数据库表结构完全一致
            # create_master_table.sql 定义了: algatop_id, name_ru, name_cn, name_en, parent_id, level, is_leaf, monthly_sales
            supabase.table("algatop_categories_master").upsert(batch).execute()
            total_synced += len(batch)
            if total_synced % 1000 == 0 or total_synced == len(unique_list):
                print(f"  Progress: {total_synced}/{len(unique_list)} synced...")
        except Exception as e:
            print(f"  Error in batch {i//batch_size}: {e}")
            # 如果报错，我们可以打印一条数据样本看看字段对不对
            if i == 0:
                print(f"  Sample row: {batch[0]}")
            break

    print(f"\n✅ Sync Complete! Total synced: {total_synced}")

if __name__ == "__main__":
    sync_to_db()
