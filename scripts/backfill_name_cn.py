import json
import os
import sys
import time
from pathlib import Path

import psycopg2
from deep_translator import GoogleTranslator, MyMemoryTranslator
from psycopg2.extras import execute_batch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MASTER_JSON = PROJECT_ROOT / "scripts" / "full_category_data.json"
CACHE_JSON = PROJECT_ROOT / "scripts" / "category_name_cn_cache.json"
DEFAULT_DB_URL = "postgresql://postgres:prosourcing123@db:5432/prosourcing"


def contains_cyrillic(value):
    text = str(value or "")
    return any("\u0400" <= ch <= "\u04FF" for ch in text)


def contains_chinese(value):
    text = str(value or "")
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def is_missing_or_invalid_cn(value):
    text = str(value or "").strip()
    if not text:
        return True
    if contains_cyrillic(text):
        return True
    return not contains_chinese(text)


def load_master_map():
    if not MASTER_JSON.exists():
        return {}

    with MASTER_JSON.open("r", encoding="utf-8-sig") as fh:
        payload = json.load(fh)

    master = payload.get("master", []) if isinstance(payload, dict) else []
    result = {}
    for item in master:
        if not isinstance(item, dict):
            continue
        ru = str(item.get("name_ru") or "").strip()
        cn = str(item.get("name_cn") or "").strip()
        if ru and cn and contains_chinese(cn):
            result[ru] = cn
    return result


def load_cache():
    if not CACHE_JSON.exists():
        return {}
    with CACHE_JSON.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    return {str(k).strip(): str(v).strip() for k, v in payload.items() if str(k).strip() and str(v).strip()}


def save_cache(cache):
    ordered = dict(sorted(cache.items(), key=lambda item: item[0]))
    with CACHE_JSON.open("w", encoding="utf-8") as fh:
        json.dump(ordered, fh, ensure_ascii=False, indent=2)


def fetch_targets(cur, table_name):
    cur.execute(
        f"""
        SELECT id_key, name_ru, name_cn
        FROM (
            SELECT algatop_id AS id_key, name_ru, name_cn
            FROM public.algatop_categories_master
            WHERE %s = 'algatop_categories_master'
            UNION ALL
            SELECT category_id AS id_key, name_ru, name_cn
            FROM public.categories
            WHERE %s = 'categories'
        ) src
        WHERE id_key IS NOT NULL
          AND COALESCE(BTRIM(name_ru), '') <> ''
          AND (name_cn IS NULL OR BTRIM(name_cn) = '' OR name_cn ~ '[А-Яа-яЁё]')
        """,
        (table_name, table_name),
    )
    return cur.fetchall()


def apply_updates(cur, table_name, rows):
    if not rows:
        return 0

    id_column = "algatop_id" if table_name == "algatop_categories_master" else "category_id"
    execute_batch(
        cur,
        f"""
        UPDATE public.{table_name}
        SET name_cn = %s
        WHERE {id_column} = %s
        """,
        [(name_cn, row_id) for row_id, name_cn in rows],
        page_size=500,
    )
    return len(rows)


def translate_one(text):
    translators = [
        GoogleTranslator(source="ru", target="zh-CN"),
        MyMemoryTranslator(source="ru-RU", target="zh-CN"),
    ]
    for translator in translators:
        try:
            result = str(translator.translate(text) or "").strip()
            if result and contains_chinese(result):
                return result
        except Exception:
            continue
    return ""


def translate_missing_texts(texts, cache):
    pending = [text for text in texts if text not in cache]
    total = len(pending)
    if not pending:
        return cache

    for index, text in enumerate(pending, start=1):
        translated = translate_one(text)
        if translated:
            cache[text] = translated
        if index % 25 == 0 or index == total:
            save_cache(cache)
            print(
                json.dumps(
                    {
                        "stage": "translate",
                        "done": index,
                        "total": total,
                        "cache_size": len(cache),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        time.sleep(0.15)

    return cache


def backfill_table(cur, table_name, translation_cache):
    targets = fetch_targets(cur, table_name)
    if not targets:
        return 0, 0

    updates = []
    resolved_count = 0
    total = len(targets)
    for index, (row_id, name_ru, _name_cn) in enumerate(targets, start=1):
        ru = str(name_ru or "").strip()
        translated = translation_cache.get(ru, "")
        if not translated:
            translated = translate_one(ru)
            if translated:
                translation_cache[ru] = translated

        if translated and contains_chinese(translated):
            updates.append((str(row_id), translated))
            resolved_count += 1

        if len(updates) >= 50:
            apply_updates(cur, table_name, updates)
            updates.clear()
            save_cache(translation_cache)
            print(
                json.dumps(
                    {
                        "stage": "backfill",
                        "table": table_name,
                        "done": index,
                        "total": total,
                        "resolved": resolved_count,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    if updates:
        apply_updates(cur, table_name, updates)
        save_cache(translation_cache)

    unresolved = total - resolved_count
    return resolved_count, unresolved


def main():
    db_url = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)
    translation_cache = load_master_map()
    translation_cache.update(load_cache())
    print(
        json.dumps(
            {
                "stage": "start",
                "cache_size": len(translation_cache),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    with psycopg2.connect(db_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            master_updated, master_unresolved = backfill_table(cur, "algatop_categories_master", translation_cache)
            categories_updated, categories_unresolved = backfill_table(cur, "categories", translation_cache)

    save_cache(translation_cache)
    print(
        json.dumps(
            {
                "algatop_categories_master_updated": master_updated,
                "algatop_categories_master_unresolved": master_unresolved,
                "categories_updated": categories_updated,
                "categories_unresolved": categories_unresolved,
                "cache_size": len(translation_cache),
            },
            ensure_ascii=False,
        )
    )
    sys.stdout.flush()


if __name__ == "__main__":
    main()
