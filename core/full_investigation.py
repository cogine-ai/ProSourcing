from supabase import create_client

SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def full_investigation():
    # 1. 分页拉取全量数据
    all_data = []
    page_size = 1000
    for i in range(5):
        res = supabase.table("categories").select("*").range(i * page_size, (i + 1) * page_size - 1).execute()
        if not res.data: break
        all_data.extend(res.data)
        if len(res.data) < page_size: break
    
    print(f"Total categories retrieved: {len(all_data)}")
    
    # 2. 分析层级
    nodes = {c['category_id']: c for c in all_data}
    adj = {}
    for c in all_data:
        pid = c['parent_category_id']
        adj.setdefault(pid, []).append(c['category_id'])
    
    # 寻找链条
    def get_path(cid, path):
        node = nodes.get(cid)
        if not node: return path
        pid = node['parent_category_id']
        if pid and pid in nodes and pid != cid:
            return get_path(pid, [pid] + path)
        return path

    max_path_len = 0
    sample_deep_path = []
    
    for cid in nodes:
        path = get_path(cid, [cid])
        if len(path) > max_path_len:
            max_path_len = len(path)
            sample_deep_path = path

    print(f"Max detected depth level: {max_path_len}")
    if sample_deep_path:
        print(f"Sample deep path: {' -> '.join(sample_deep_path)}")

    # 3. 统计中文
    cn_count = sum(1 for c in all_data if '(' in c['category_name'])
    print(f"Total entries with Chinese (brackets): {cn_count}")
    
    # 4. 检查是否有 category_name_cn 字段非空
    cn_field_count = sum(1 for c in all_data if c.get('category_name_cn'))
    print(f"Total entries with category_name_cn populated: {cn_field_count}")

if __name__ == "__main__":
    full_investigation()
