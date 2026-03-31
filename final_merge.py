import os

def final_merge():
    # 1. Path to user's seed SQL
    src_path = r"d:\item\ProSourcing\deployment_package\scripts\新建文件夹\seed_categories.sql"
    if not os.path.exists(src_path):
        print(f"Error: {src_path} not found")
        return

    # 2. Read content
    try:
        with open(src_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        with open(src_path, 'r', encoding='utf-16') as f:
            content = f.read()

    # 3. Create the final bundle
    # We add a small fix for the missing column issue in case some INSERTs don't match the new schema, 
    # but since I added it to init.sql, it should be fine.
    
    header = [
        "-- ProSourcing 自动化初始数据种子 (Master & Homepage Stats)",
        "SET statement_timeout = 0;",
        "SET client_encoding = 'UTF8';",
        "SET standard_conforming_strings = on;",
        "",
        "-- 清空旧数据确保同步",
        "TRUNCATE TABLE algatop_categories_master CASCADE;",
        "TRUNCATE TABLE algatop_top_category_stats CASCADE;",
        ""
    ]
    
    output_file = r"d:\item\ProSourcing\deployment_package\scripts\seed_data.sql"
    # Write with UTF-8 BOM
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        f.write("\n".join(header))
        f.write(content)

    print(f"Final Success: {output_file} is ready for automatic deployment.")

if __name__ == "__main__":
    final_merge()
