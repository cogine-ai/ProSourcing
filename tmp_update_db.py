import psycopg2

try:
    conn = psycopg2.connect('postgresql://postgres:prosourcing123@localhost:5432/prosourcing')
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute('''
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='analysis_tasks' AND COLUMN_NAME='updated_at') THEN
            ALTER TABLE public.analysis_tasks ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now());
        END IF;
    END $$;
    ''')
    print('DATABASE UPDATED SUCCESSFULLY')
except Exception as e:
    print('ERROR:', e)
