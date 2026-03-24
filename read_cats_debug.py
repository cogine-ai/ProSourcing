import json
import os

def read_utf16_json_and_print():
    path = r"d:\item\ProSourcing\cats_debug_2.json"
    if not os.path.exists(path):
        print(f"Error: {path} not found")
        return

    with open(path, 'r', encoding='utf-16') as f:
        data = json.load(f)
    
    print(json.dumps(data[:5], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    read_utf16_json_and_print()
