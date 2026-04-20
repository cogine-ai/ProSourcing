import json
path = r'scripts\kaspi_full_tree_raw.json'
data = json.load(open(path, encoding='utf-8-sig'))

def walk(node):
    codes = node.get('categoryCodes', [])
    title = node.get('title', '')
    if not node.get('subNodes'):
        print(f"Leaf: {title} | Codes: {codes}")
    else:
        for child in node['subNodes']:
            walk(child)

# 只打印前 10 个叶子节点看看
count = 0
def walk_limited(node):
    global count
    if count >= 10: return
    codes = node.get('categoryCodes', [])
    title = node.get('title', '')
    if not node.get('subNodes'):
        print(f"Leaf: {title} | Codes: {codes}")
        count += 1
    else:
        for child in node['subNodes']:
            walk_limited(child)

walk_limited(data)
