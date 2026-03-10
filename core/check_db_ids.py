import sqlite3
import os

db_path = "d:/item/ProSourcing/backend/database.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查是否有已经存在的 algatop_id
cursor.execute("SELECT category_name, algatop_id FROM global_category_dict WHERE algatop_id IS NOT NULL AND algatop_id != ''")
rows = cursor.fetchall()

if not rows:
    print("No algatop_id found in database.")
else:
    print(f"Found {len(rows)} categories with algatop_id:")
    for name, aid in rows[:20]:
        print(f"  {name}: {aid}")

conn.close()
