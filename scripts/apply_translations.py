import json
import psycopg2

DB_URL = "postgresql://postgres:prosourcing123@localhost:5432/prosourcing"
CACHE_PATH = "d:/item/ProSourcing/scripts/category_name_cn_cache.json"

def run():
    # 1. 加载所有批次的翻译
    all_translations = {}
    batches = [
        "d:/item/ProSourcing/scripts/translations_batch_1.json",
        "d:/item/ProSourcing/scripts/translations_batch_2.json",
        "d:/item/ProSourcing/scripts/translations_batch_3.json",
        "d:/item/ProSourcing/scripts/translations_final.json"
    ]
    for path in batches:
        with open(path, "r", encoding="utf-8") as f:
            all_translations.update(json.load(f))
    
    print(f"Loaded {len(all_translations)} new translations.")

    # 2. 更新数据库
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    print("Updating database...")
    count = 0
    for ru, cn in all_translations.items():
        # 更新数据库
        # 注意：category_name 也需要更新以包含翻译
        display_name = f"{ru} ({cn})"
        cur.execute(
            "UPDATE categories SET name_cn = %s, category_name = %s WHERE name_ru = %s AND name_cn IS NULL",
            (cn, display_name, ru)
        )
        if cur.rowcount > 0:
            count += 1
    
    conn.commit()
    print(f"Database updated: {count} records.")

    # 3. 更新缓存文件
    print("Updating cache file...")
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except:
        cache = {}
    
    cache.update(all_translations)
    
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    print(f"Cache updated: {len(cache)} total items.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    run()
