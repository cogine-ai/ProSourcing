import psycopg2
conn = psycopg2.connect('postgresql://postgres:prosourcing123@localhost:5432/prosourcing')
cur = conn.cursor()
cur.execute("SELECT count(*) FROM categories WHERE algatop_id ~ '^[0-9]+$'")
print(f"Numeric IDs: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM categories WHERE algatop_id IS NOT NULL AND algatop_id != ''")
print(f"Non-empty IDs: {cur.fetchone()[0]}")
cur.close()
conn.close()
