import json
import os
import sys
from datetime import datetime

# 设置项目根目录
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.final_pipeline import supabase

def sync_tree_to_db():
    json_path = "kaspi_full_tree_raw.json"
    if not os.path.exists(json_path):
        print(f"❌ 找不到原始数据文件: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    all_categories = []
    
    def process_node(node, parent_id=None):
        cat_id = node.get('code')
        if not cat_id: return

        # 获取产品数 (popularity 字段)
        qty = 0
        if 'data' in node and node['data'] and 'popularity' in node['data']:
            qty = node['data']['popularity']
        
        # 组装数据项
        cat_data = {
            "category_id": cat_id,
            "category_name": node.get('title', ''),
            "sale_product_qty": qty,
            "parent_category_id": parent_id,
            "is_top_level": (node.get('level') == 1),
            "last_sync_at": datetime.utcnow().isoformat()
        }
        all_categories.append(cat_data)

        # 递归处理子节点
        if 'subNodes' in node and node['subNodes']:
            for sub in node['subNodes']:
                process_node(sub, cat_id)

    print("🔍 正在解析类目树...")
    if 'subNodes' in raw_data:
        for root_node in raw_data['subNodes']:
            process_node(root_node)

    print(f"📦 解析完成，准备同步 {len(all_categories)} 条数据记录到数据库...")
    
    # 分批入库 (每批把 100 条)
    batch_size = 100
    success_count = 0
    
    for i in range(0, len(all_categories), batch_size):
        batch = all_categories[i:i + batch_size]
        try:
            # 使用 upsert，如果 ID 已存在则更新
            supabase.table("categories").upsert(batch, on_conflict="category_id").execute()
            success_count += len(batch)
            print(f"  ✅ 已同步 {success_count}/{len(all_categories)}...")
        except Exception as e:
            print(f"  ❌ 批次同步失败 (索引 {i}): {e}")

    print(f"\n✨ 全量类目同步任务完成！总计成功: {success_count} 条。")
    print("哥，现在数据库里已经有整棵树了，下一步我直接开搞前端抽屉。")

if __name__ == "__main__":
    sync_tree_to_db()
