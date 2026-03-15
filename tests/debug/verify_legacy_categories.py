from supabase import create_client

SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def analyze_categories_structure():
    print("Fetching all records from 'categories' table...")
    res = supabase.table("categories").select("category_id, category_name, parent_category_id, is_top_level").limit(5000).execute()
    data = res.data
    print(f"Total records found: {len(data)}")

    # 建图
    adj = {}
    nodes = {}
    for c in data:
        cid = c['category_id']
        pid = c['parent_category_id']
        nodes[cid] = c
        if pid not in adj: adj[pid] = []
        adj[pid].append(cid)

    # 计算深度
    def get_max_depth(cid, current_depth):
        children = adj.get(cid, [])
        if not children:
            return current_depth
        return max([get_max_depth(child, current_depth + 1) for child in children])

    # 找到顶级节点 (parent 为空或某些特定标识)
    roots = [c['category_id'] for c in data if not c['parent_category_id'] or c['parent_category_id'] == 'desktop-menu']
    print(f"Root nodes detected: {len(roots)}")
    
    if roots:
        max_d = max([get_max_depth(r, 1) for r in roots])
        print(f"Max hierarchy depth: {max_d}")
    else:
        print("No root nodes found via parent_category_id investigation.")

    # 统计中文占比
    chinese_count = sum(1 for c in data if '(' in c['category_name'] and ')' in c['category_name'])
    print(f"Records with brackets (suspected Chinese): {chinese_count}")

if __name__ == "__main__":
    analyze_categories_structure()
