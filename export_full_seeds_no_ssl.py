import os
import json
import httpx

SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"

def export_supabase_to_sql_no_ssl():
    print("Connecting to Supabase (SSL Verify OFF)...")
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    try:
        with httpx.Client(verify=False) as client:
            # Fetch some regular categories for the dictionary (limit to 3000 to keep it manageable)
            r = client.get(f"{SUPABASE_URL}/rest/v1/algatop_categories_master?select=*&limit=3000", headers=headers)
            master_data = r.json()
            print(f"Fetched {len(master_data)} dictionary entries.")

            # Fetch stats
            r = client.get(f"{SUPABASE_URL}/rest/v1/algatop_top_category_stats?select=*", headers=headers)
            stats = r.json()
            print(f"Fetched {len(stats)} stats rows.")
    except Exception as e:
        print(f"Error fetching: {e}")
        return

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
            if k == 'leaf_count': continue # skip if not in schema
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

    for row in stats:
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

    output_dir = r"d:\item\ProSourcing\deployment_package\scripts"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_file = os.path.join(output_dir, "seed_data.sql")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(sql_lines))
    
    print(f"Success: {output_file} updated with {len(sql_lines)} lines.")

if __name__ == "__main__":
    export_supabase_to_sql_no_ssl()
