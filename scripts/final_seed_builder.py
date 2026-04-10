import os

def generate_final_seed():
    src_path = r"d:\item\ProSourcing\deployment_package\scripts\新建文件夹\seed_categories.sql"
    if not os.path.exists(src_path):
        print(f"Error: {src_path} not found")
        return

    print("Step 1: Reading source (UTF-16LE)...")
    # Read binary and decode as UTF-16
    with open(src_path, 'rb') as f:
        raw_data = f.read()
    content = raw_data.decode('utf-16')

    # Step 2: Prepare Header
    header = [
        "-- ProSourcing 21大类全血版初始数据种子 (UTF-8 纯净版)",
        "SET statement_timeout = 0;",
        "SET client_encoding = 'UTF8';",
        "SET standard_conforming_strings = on;",
        "",
        "-- 清空旧数据确保同步",
        "TRUNCATE TABLE algatop_categories_master CASCADE;",
        "TRUNCATE TABLE algatop_top_category_stats CASCADE;",
        ""
    ]
    
    # Step 3: Process content
    # We remove 'public.' to be safer with default schema settings
    clean_content = content.replace("public.algatop_categories_master", "algatop_categories_master")
    clean_content = clean_content.replace("public.algatop_top_category_stats", "algatop_top_category_stats")
    
    # Optional: ensure we only keep INSERTs with actual data if there's header junk
    # Actually, keep the whole thing as it's a valid SQL script once decoded
    
    dest_path = r"d:\item\ProSourcing\deployment_package\scripts\seed_data.sql"
    
    print(f"Step 2: Writing to {dest_path} as UTF-8...")
    # Write as plain UTF-8 (no BOM) for best Linux compatibility
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(header))
        f.write("\n")
        f.write(clean_content)

    print(f"Final Success: {dest_path} is now 100% ready.")
    print(f"- Processed file size: {len(clean_content)} chars")

if __name__ == "__main__":
    generate_final_seed()
