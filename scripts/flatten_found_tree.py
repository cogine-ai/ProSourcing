import json

def flatten_tree(nodes, flattened=None):
    if flattened is None:
        flattened = []
    for node in nodes:
        flattened.append({
            "id": node["id"],
            "name": node["name"]
        })
        if node.get("children"):
            flatten_tree(node["children"], flattened)
    return flattened

with open("d:/item/ProSourcing/tmp/root-artifacts/全部分类信息.txt", "r", encoding="utf-8") as f:
    data = json.load(f)

flat_list = flatten_tree(data)
print(f"Total items in file: {len(flat_list)}")

# 保存为标准 JSON 备用
with open("scripts/algatop_full_tree_flattened.json", "w", encoding="utf-8") as f:
    json.dump(flat_list, f, ensure_ascii=False, indent=2)
