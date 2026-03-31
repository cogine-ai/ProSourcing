from core.final_pipeline import supabase as sb
import json

def check():
    res_a = sb.table('categories').select('*').eq('is_top_level', True).execute()
    print(f"Algatop Total: {len(res_a.data)}")
    for r in res_a.data:
        print(f"ID: {r['category_id']} | RU: {r['category_name']} | CN: {r['category_name_cn']}")

    res_k = sb.table('global_category_dict').select('*').eq('parent_kaspi_id', 'desktop-menu').execute()
    print(f"\nKaspi Dict Top Total: {len(res_k.data)}")
    for r in res_k.data:
        print(f"KID: {r['kaspi_id']} | RU: {r['name_ru']} | CN: {r['name_cn']} | AID: {r['algatop_id']}")

if __name__ == "__main__":
    check()
