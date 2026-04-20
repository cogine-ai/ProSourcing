import psycopg2
conn = psycopg2.connect('postgresql://postgres:prosourcing123@localhost:5432/prosourcing')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
tables = cur.fetchall()
for t in tables:
    cur.execute(f"SELECT count(*) FROM {t[0]}")
    count = cur.fetchone()[0]
    print(f"Table: {t[0]}, Rows: {count}")
cur.close()
conn.close()
