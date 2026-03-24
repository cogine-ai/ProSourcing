import os

def final_fix_full_blood():
    # 1. Source (UTF-16LE)
    src_path = r"d:\item\ProSourcing\deployment_package\scripts\新建文件夹\seed_categories.sql"
    if not os.path.exists(src_path):
        print(f"Error: {src_path} not found")
        return

    print(f"Reading {src_path} as UTF-16LE...")
    with open(src_path, 'r', encoding='utf-16') as f:
        content = f.read()

    # 2. Header for Postgres compatibility
    # Ensure it's clean and truncates existing junk
    header = [
        "-- ProSourcing 21大类全血版数据种子 (UTF-8 兼容)",
        "SET statement_timeout = 0;",
        "SET client_encoding = 'UTF8';",
        "SET standard_conforming_strings = on;",
        "",
        "TRUNCATE TABLE algatop_categories_master CASCADE;",
        "TRUNCATE TABLE algatop_top_category_stats CASCADE;",
        ""
    ]
    
    # 3. Write to the destination in standard UTF-8
    dest_path = r"d:\item\ProSourcing\deployment_package\scripts\seed_data.sql"
    
    # Force clean up some common pg_dump residue if any
    # (Optional: check for specific columns mismatch)
    
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(header))
        f.write(content)

    print(f"Success! {dest_path} is now UTF-8 and contains the full content.")
    
    # Check for 21 categories in the content
    count = content.count("INSERT INTO algatop_top_category_stats")
    print(f"Verification: Found {count} root category stats inserts.")

if __name__ == "__main__":
    final_fix_full_blood()
