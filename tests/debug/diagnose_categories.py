from core.final_pipeline import supabase as sb
import json

def diagnose():
    # 1. Check top stats for Dashboard
    res_tops = sb.table('global_category_dict').select('*').eq('is_top_level', True).execute()
    print(f"--- Top categories for Dashboard (Total: {len(res_tops.data)}) ---")
    for r in sorted(res_tops.data, key=lambda x: x.get('monthly_sales', 0) or 0, reverse=True):
        print(f"ID: {r['kaspi_id']} | CN: {r['name_cn']} | RU: {r['name_ru']} | Sales: {r['monthly_sales']} | Qty: {r['sale_product_qty']}")

    # 2. Check Kaspi Root structure for the Tree
    res_kaspi_roots = sb.table('global_category_dict').select('*').eq('parent_kaspi_id', 'desktop-menu').execute()
    print(f"\n--- Root nodes for Tree (Parent is desktop-menu, Total: {len(res_kaspi_roots.data)}) ---")
    for r in res_kaspi_roots.data:
        print(f"KID: {r['kaspi_id']} | CN: {r['name_cn']} | RU: {r['name_ru']} | IsLeaf: {r['is_leaf']}")

    # 3. Check if desktop-menu itself is there
    res_dm = sb.table('global_category_dict').select('*').eq('kaspi_id', 'desktop-menu').execute()
    print(f"\n--- desktop-menu itself ---")
    print(res_dm.data)

if __name__ == "__main__":
    diagnose()
