import re
import os

def read_and_clean_sql():
    # 1. Path to user's seed SQL
    src_path = r"d:\item\ProSourcing\deployment_package\scripts\新建文件夹\seed_categories.sql"
    if not os.path.exists(src_path):
        print(f"Error: {src_path} not found")
        return

    # 2. Read content (handling encoding)
    try:
        with open(src_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        with open(src_path, 'r', encoding='utf-16') as f:
            content = f.read()

    # 3. Extract relevant INSERT statements or the whole data part
    # We want to keep SET client_encoding and INSERTs
    clean_lines = [
        "SET statement_timeout = 0;",
        "SET client_encoding = 'UTF8';",
        "SET standard_conforming_strings = on;",
        "",
        "TRUNCATE TABLE algatop_categories_master CASCADE;",
        "TRUNCATE TABLE algatop_top_category_stats CASCADE;",
        ""
    ]
    
    # Simple regex to find INSERT statements
    insert_pattern = re.compile(r"INSERT INTO .*?;", re.DOTALL)
    inserts = insert_pattern.findall(content)
    
    print(f"Found {len(inserts)} INSERT statements.")
    
    for ins in inserts:
        # Just ensure they end with semicolon and newline
        clean_lines.append(ins.strip())
        
    output_file = r"d:\item\ProSourcing\deployment_package\scripts\seed_data.sql"
    # Write with UTF-8 BOM to prevent PowerShell encoding issues
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        f.write("\n\n".join(clean_lines))

    print(f"Success: {output_file} updated with {len(inserts)} clean entries.")

if __name__ == "__main__":
    read_and_clean_sql()
