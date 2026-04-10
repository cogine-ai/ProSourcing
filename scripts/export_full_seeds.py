import os
import json
import requests
from supabase import create_client, Client

SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"

def export_supabase_to_sql():
    print("Connecting to Supabase...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. Export algatop_categories_master
    print("Fetching algatop_categories_master...")
    master_data = []
    page_size = 1000
    for i in range(20): # Up to 20000 rows
        res = supabase.table("algatop_categories_master").select("*").range(i*page_size, (i+1)*page_size - 1).execute()
        if not res.data: break
        master_data.extend(res.data)
        if len(res.data) < page_size: break
    
    print(f"Fetched {len(master_data)} rows for master.")

    # 2. Export algatop_top_category_stats
    print("Fetching algatop_top_category_stats...")
    stats_data = supabase.table("algatop_top_category_stats").select("*").execute().data
    print(f"Fetched {len(stats_data)} rows for stats.")

    # 3. Generate SQL
    sql_lines = [
        "-- ProSourcing 完整初始数据同步脚本 (含主字典与首页统计)",
        "TRUNCATE TABLE algatop_categories_master CASCADE;",
        "TRUNCATE TABLE algatop_top_category_stats CASCADE;"
    ]

    for row in master_data:
        cols = []
        vals = []
        for k, v in row.items():
            cols.append(k)
            if v is None:
                vals.append("NULL")
            elif isinstance(v, str):
                v_clean = v.replace("'", "''")
                vals.append(f"'{v_clean}'")
            elif isinstance(v, bool):
                vals.append(str(v).upper())
            else:
                vals.append(str(v))
        
        sql = f"INSERT INTO algatop_categories_master ({', '.join(cols)}) VALUES ({', '.join(vals)}) ON CONFLICT (algatop_id) DO NOTHING;"
        sql_lines.append(sql)

    for row in stats_data:
        cols = []
        vals = []
        for k, v in row.items():
            cols.append(k)
            if v is None:
                vals.append("NULL")
            elif isinstance(v, str):
                v_clean = v.replace("'", "''")
                vals.append(f"'{v_clean}'")
            elif isinstance(v, bool):
                vals.append(str(v).upper())
            else:
                vals.append(str(v))
        
        sql = f"INSERT INTO algatop_top_category_stats ({', '.join(cols)}) VALUES ({', '.join(vals)}) ON CONFLICT (algatop_id) DO NOTHING;"
        sql_lines.append(sql)

    output_file = r"d:\item\ProSourcing\deployment_package\scripts\seed_data.sql"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(sql_lines))
    
    print(f"Success: {output_file} updated with full data.")

if __name__ == "__main__":
    export_supabase_to_sql()
