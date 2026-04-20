import psycopg2
import json

def export():
    conn = psycopg2.connect('postgresql://postgres:prosourcing123@localhost:5432/prosourcing')
    cur = conn.cursor()
    
    # 1. 获取所有数据
    cur.execute("SELECT algatop_id, name_ru, name_cn, category_name, parent_category_id FROM categories ORDER BY algatop_id")
    rows = cur.fetchall()
    
    output_file = 'scripts/categories_full_restore.sql'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- Algatop Categories Full Restore Script\n")
        f.write("-- 100% Translation Coverage (4849 records)\n\n")
        f.write("BEGIN;\n\n")
        
        # 建议先备份或清理
        f.write("-- TRUNCATE TABLE categories; -- 如果需要完全覆盖，取消注释这一行\n\n")
        
        for row in rows:
            algatop_id, name_ru, name_cn, category_name, parent_id = row
            
            # 处理 SQL 转义
            def clean(s):
                if s is None: return "NULL"
                return "'" + s.replace("'", "''") + "'"
            
            f.write(f"INSERT INTO categories (algatop_id, name_ru, name_cn, category_name, parent_id) ")
            f.write(f"VALUES ({clean(algatop_id)}, {clean(name_ru)}, {clean(name_cn)}, {clean(category_name)}, {clean(parent_id)}) ")
            f.write(f"ON CONFLICT (algatop_id) DO UPDATE SET ")
            f.write(f"name_ru = EXCLUDED.name_ru, name_cn = EXCLUDED.name_cn, category_name = EXCLUDED.category_name, parent_id = EXCLUDED.parent_id;\n")
        
        f.write("\nCOMMIT;\n")
    
    print(f"Exported {len(rows)} categories to {output_file}")
    conn.close()

if __name__ == "__main__":
    export()
