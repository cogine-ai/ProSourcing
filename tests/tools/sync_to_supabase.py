import json
from supabase import create_client, Client
from deep_translator import GoogleTranslator

SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def flatten_tree(nodes, flat_list):
    for n in nodes:
        # Clone and remove children for flattening
        item = {
            "id": n["id"],
            "name": n["name"],
            "parent_id": n["parent_id"],
            "level": n["level"]
        }
        flat_list.append(item)
        if n.get("children"):
            flatten_tree(n["children"], flat_list)

def sync_data():
    print("Reading extracted tree...")
    with open("d:/item/ProSourcing/output/algatop_full_tree.json", "r", encoding="utf-8") as f:
        tree = json.load(f)
        
    flat_nodes = []
    flatten_tree(tree, flat_nodes)
    print(f"Flattened to {len(flat_nodes)} nodes.")
    
    # 哥，为了防止接口超时，我们分批插入 (每批 50 条)
    batch_size = 50
    total_synced = 0
    
    # 步骤 1: 清空旧数据 (谨慎操作，如果是系统唯一表)
    # 考虑到用户需求是“以 Algatop 为准”，我们直接全量更新
    print("Clearing old data from global_category_dict...")
    # 注意: 如果没有 service_role key，delete * 可能不被允许。
    # 我们尝试用 UPSERT 逻辑或者如果有权限则直接删除
    try:
        # 先删除所有 (如果权限允许)
        supabase.table("global_category_dict").delete().neq("algatop_id", "-1").execute()
    except Exception as e:
        print(f"Delete warning (probably no batch delete permission): {e}")

    print("Inserting/Upserting new Algatop data...")
    translator = GoogleTranslator(source='auto', target='zh-CN')
    
    for i in range(0, len(flat_nodes), batch_size):
        batch = flat_nodes[i:i+batch_size]
        rows = []
        for node in batch:
            # 翻译中文名 (可选，先拿前 3 个层级的进行翻译以加速)
            cn_name = node['name']
            if node['level'] <= 2:
                try: 
                    # cn_name = translator.translate(node['name']) 
                    # 哥，为了同步速度，翻译我先注掉，等入库后用专门的脚本刷，或者前端调翻译
                    pass
                except: pass
                
            rows.append({
                "kaspi_id": node['id'], # 以 Algatop ID 作为系统内的根 ID
                "algatop_id": node['id'],
                "name_ru": node['name'],
                "name_cn": cn_name, # 先存俄文，之后刷翻译
                "parent_kaspi_id": node['parent_id'],
                "is_leaf": 1 if len(node.get("children", [])) == 0 else 0,
                "is_top_level": 1 if node['level'] == 0 else 0
            })
            
        try:
            supabase.table("global_category_dict").upsert(rows).execute()
            total_synced += len(rows)
            print(f"  Synced {total_synced}/{len(flat_nodes)} nodes...")
        except Exception as e:
            print(f"  Error in batch: {e}")

    print(f"\nSuccessfully synced {total_synced} nodes to Supabase.")

if __name__ == "__main__":
    sync_data()
