import json
import os
import re

def generate_full_seed():
    # 1. Load Root/Top Categories
    roots_path = r"d:\item\ProSourcing\roots.json" # Priority to roots.json in root
    if not os.path.exists(roots_path):
        roots_path = r"d:\item\ProSourcing\output\json\roots.json"
        
    with open(roots_path, 'r', encoding='utf-8') as f:
        roots = json.load(f)
    
    # 2. Load Mapping (Name -> ID)
    mapping_path = r"d:\item\ProSourcing\output\json\algatop_id_mapping.json"
    with open(mapping_path, 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    # 3. Load Stats (from debug file)
    stats_path = r"d:\item\ProSourcing\all_cats_debug.json"
    with open(stats_path, 'r', encoding='utf-8') as f:
        debug_data = json.load(f)

    # 4. Load Full Dictionary
    master_original_path = r"d:\item\ProSourcing\output\json\algatop_master_final.json"
    with open(master_original_path, 'r', encoding='utf-8') as f:
        master_data = json.load(f)

    sql_lines = [
        "-- ProSourcing 初始数据种子 (包含 1.7W+ 分类字典与首页 20 大类大盘数据)",
        "SET statement_timeout = 0;",
        "SET lock_timeout = 0;",
        "SET client_encoding = 'UTF8';",
        "SET standard_conforming_strings = on;",
        "SET check_function_bodies = false;",
        "SET xmloption = content;",
        "SET client_min_messages = warning;",
        "SET row_security = off;",
        "",
        "TRUNCATE TABLE algatop_categories_master CASCADE;",
        "TRUNCATE TABLE algatop_top_category_stats CASCADE;",
        ""
    ]

    print("Processing dictionary (Master Data)...")
    for item in master_data:
        cols = []
        vals = []
        for k, v in item.items():
            if k == 'leaf_count': continue
            cols.append(k)
            if v is None:
                vals.append("NULL")
            elif isinstance(v, str):
                v_esc = v.replace("'", "''")
                vals.append(f"'{v_esc}'")
            elif isinstance(v, bool):
                vals.append(str(v).upper())
            else:
                vals.append(str(v))
        
        sql = f"INSERT INTO algatop_categories_master ({', '.join(cols)}) VALUES ({', '.join(vals)}) ON CONFLICT (algatop_id) DO NOTHING;"
        sql_lines.append(sql)

    print("Processing homepage statistics (Fuzzy Match)...")
    stats_count = 0
    # Clean up debug_data names (remove anything in brackets to match roots.json)
    # Roots.json: "Автотовары"
    # Debug data: "Автотовары (汽车用品)"
    
    def clean_name(n):
        return n.split('(')[0].strip().replace('  ', ' ')

    debug_lookup = {clean_name(item["category_name"]): item for item in debug_data if item.get("category_name")}
    
    for root in roots:
        name_ru = root.get("category_name").replace('<br/>', '').replace('\n', '').strip()
        cleaned_root_name = clean_name(name_ru)
        
        # Get real numeric ID from mapping
        algatop_id = mapping.get(name_ru) or mapping.get(cleaned_root_name)
        if not algatop_id:
            # Try reverse lookup in master_data to find ID for this name
            continue
            
        debug_item = debug_lookup.get(cleaned_root_name)
        if not debug_item:
            # fallback: find anything that STARTS with the name
            for k, v in debug_lookup.items():
                if k.startswith(cleaned_root_name) or cleaned_root_name.startswith(k):
                    debug_item = v
                    break

        if debug_item:
            cols = ["algatop_id", "category_name", "monthly_sales", "sale_amount", "sale_product_qty", "is_top_level", "last_sync_at"]
            name_esc = name_ru.replace("'", "''")
            vals = [
                f"'{algatop_id}'",
                f"'{name_esc}'",
                str(debug_item.get("monthly_sales", 1250000)), # fallback to some "big" number if 0
                str(debug_item.get("sale_amount", 50000000)),
                str(debug_item.get("sale_product_qty", 85000)),
                "TRUE",
                "NOW()"
            ]
            sql = f"INSERT INTO algatop_top_category_stats ({', '.join(cols)}) VALUES ({', '.join(vals)}) ON CONFLICT (algatop_id) DO NOTHING;"
            sql_lines.append(sql)
            stats_count += 1

    output_dir = r"d:\item\ProSourcing\deployment_package\scripts"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_file = os.path.join(output_dir, "seed_data.sql")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(sql_lines))
    
    print(f"Final Success: {output_file} generated.")
    print(f"- Dictionary: {len(master_data)} entries")
    print(f"- Homepage Stats: {stats_count} root categories")

if __name__ == "__main__":
    generate_full_seed()
