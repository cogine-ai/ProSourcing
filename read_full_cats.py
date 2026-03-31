import json
import os

def read_utf16_json_and_print():
    path = r"d:\item\ProSourcing\deployment_package\scripts\新建文件夹\full_category_data.json"
    if not os.path.exists(path):
        print(f"Error: {path} not found")
        return

    # Try UTF-8 first, then UTF-16
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        with open(path, 'r', encoding='utf-16') as f:
            data = json.load(f)
    
    # Print root categories count and examples
    roots = [i for i in data if i.get('is_top_level')]
    print(f"Total entries: {len(data)}")
    print(f"Root categories found: {len(roots)}")
    for r in roots[:21]:
        print(f"ID: {r.get('algatop_id')}, Name: {r.get('category_name')}, Sales: {r.get('monthly_sales')}")

if __name__ == "__main__":
    read_utf16_json_and_print()
