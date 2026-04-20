"""
从当前数据库导出完美的 full_category_data.json 种子文件。
格式完全兼容 seed_db_from_json.py 的消费格式：
{
    "seed_meta": {...},
    "master": [...],       # algatop_categories_master 全量
    "stats": [...],        # algatop_top_category_stats 全量
    "tree_name_cn_map": {} # name_ru -> name_cn 映射
}
"""
import json
import psycopg2
from datetime import datetime

DB_URL = "postgresql://postgres:prosourcing123@localhost:5432/prosourcing"
OUTPUT = "scripts/full_category_data.json"


def export():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # 1. 导出 algatop_categories_master
    cur.execute("""
        SELECT algatop_id, name_ru, name_cn, name_en, parent_id, 
               level, is_leaf, monthly_sales
        FROM algatop_categories_master
        ORDER BY algatop_id
    """)
    columns = [desc[0] for desc in cur.description]
    master = []
    for row in cur.fetchall():
        item = dict(zip(columns, row))
        # 确保布尔值正确
        item["is_leaf"] = bool(item.get("is_leaf", False))
        # 确保数值不为 None
        item["monthly_sales"] = item.get("monthly_sales") or 0
        master.append(item)

    print(f"Exported master: {len(master)} records")

    # 2. 导出 algatop_top_category_stats
    cur.execute("""
        SELECT algatop_id, sales_qty, revenue, product_count, seller_count, brand_count
        FROM algatop_top_category_stats
        ORDER BY algatop_id
    """)
    columns_s = [desc[0] for desc in cur.description]
    stats = []
    for row in cur.fetchall():
        item = dict(zip(columns_s, row))
        # 数值兜底
        for k in ["sales_qty", "revenue", "product_count", "seller_count", "brand_count"]:
            item[k] = item.get(k) or 0
        stats.append(item)

    print(f"Exported stats: {len(stats)} records")

    # 3. 构建 tree_name_cn_map (name_ru -> name_cn)
    tree_name_cn_map = {}
    for item in master:
        ru = (item.get("name_ru") or "").strip()
        cn = (item.get("name_cn") or "").strip()
        if ru and cn:
            tree_name_cn_map[ru] = cn

    print(f"Exported tree_name_cn_map: {len(tree_name_cn_map)} entries")

    # 4. 验证
    missing_cn = sum(1 for m in master if not (m.get("name_cn") or "").strip())
    if missing_cn > 0:
        print(f"WARNING: {missing_cn} records still missing name_cn!")
    else:
        print("OK: All records have name_cn - 100% coverage")

    # 5. 组装输出
    payload = {
        "seed_meta": {
            "version": datetime.now().strftime("%Y-%m-%d-db-export"),
            "master_count": len(master),
            "stats_count": len(stats),
            "tree_name_cn_map_count": len(tree_name_cn_map),
            "source": "exported_from_verified_database",
            "exported_at": datetime.now().isoformat(),
        },
        "master": master,
        "stats": stats,
        "tree_name_cn_map": tree_name_cn_map,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\nDONE: Saved to {OUTPUT} ({len(master)} master, {len(stats)} stats)")

    cur.close()
    conn.close()


if __name__ == "__main__":
    export()
