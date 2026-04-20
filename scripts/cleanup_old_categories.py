#!/usr/bin/env python3
import psycopg2

DB_URL = "postgresql://postgres:prosourcing123@localhost:5432/prosourcing"

def cleanup():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # 哥，删除所有 category_id 不是纯数字的记录
        print("正在清理非数字 ID 的旧类目...")
        cur.execute("DELETE FROM categories WHERE category_id !~ '^[0-9]+$'")
        deleted_count = cur.rowcount
        
        conn.commit()
        print(f"✅ 成功删除 {deleted_count} 条旧类目数据！")
        
        # 验证一下现在的一级分类
        cur.execute("SELECT count(*) FROM categories WHERE is_top_level = True")
        top_count = cur.fetchone()[0]
        print(f" - 当前一级分类数量: {top_count}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ 清理失败: {e}")

if __name__ == "__main__":
    cleanup()
