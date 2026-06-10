
from core.final_pipeline import supabase as sb

def fix_leaf_nodes():
    print("🚀 开始修复数据库中叶子节点的 is_leaf 标识...")
    
    # 1. 获取全量类目
    res = sb.table("categories").select("category_id, parent_category_id").execute()
    all_cats = res.data
    print(f"📊 数据库当前总类目数: {len(all_cats)}")
    
    # 2. 统计哪些节点是别人的父节点
    parent_ids = set()
    for cat in all_cats:
        pid = cat.get('parent_category_id')
        if pid:
            parent_ids.add(pid)
    
    # 3. 筛选谁不是父节点（即叶子节点）
    leaf_ids = []
    parent_node_ids = []
    for cat in all_cats:
        cat_id = cat['category_id']
        if cat_id not in parent_ids:
            leaf_ids.append(cat_id)
        else:
            parent_node_ids.append(cat_id)
            
    print(f"🎯 识别出叶子节点（最小分类）数量: {len(leaf_ids)}")
    
    # 4. 批量更新数据库 (Supabase 的 in 过滤器)
    batch_size = 100
    success_count = 0
    
    for i in range(0, len(leaf_ids), batch_size):
        batch = leaf_ids[i:i + batch_size]
        try:
            sb.table("categories").update({"is_leaf": True}).in_("category_id", batch).execute()
            success_count += len(batch)
            if success_count % 500 == 0:
                print(f"  ✅ 已修复 {success_count} 个叶子节点...")
        except Exception as e:
            print(f"  ❌ 批次更新失败: {e}")

    for i in range(0, len(parent_node_ids), batch_size):
        batch = parent_node_ids[i:i + batch_size]
        try:
            sb.table("categories").update({"is_leaf": False}).in_("category_id", batch).execute()
        except Exception as e:
            print(f"  ❌ 父节点批次更新失败: {e}")
            
    print(f"\n✨ 修复完成！总计更新 {success_count} 个最小分类标识。")
    print("哥，现在你再去前端点展开，应该已经可以看到分类列表了。")

if __name__ == "__main__":
    fix_leaf_nodes()
