import os
from supabase import create_client, Client

SUPABASE_URL = "https://furwnoxzsddkytimxtma.supabase.co"
SUPABASE_KEY = "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H" # 注意：这通常不是 service_role key，可能无法执行 DDL。
# 哥，如果这个 key 权限不够，你需要在 Supabase 控制台跑一下这个 SQL。

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

migration_sql = """
-- 1. 创建任务主表
CREATE TABLE IF NOT EXISTS public.analysis_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, crawling, scoring, completed, failed
    progress INTEGER DEFAULT 0,
    excel_path TEXT,
    error_msg TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. 扩展原始数据表 (增加 task_id)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='products_raw_data' AND COLUMN_NAME='task_id') THEN
        ALTER TABLE public.products_raw_data ADD COLUMN task_id UUID REFERENCES public.analysis_tasks(id) ON DELETE CASCADE;
    END IF;
END $$;

-- 3. 扩展指标计算表 (增加 task_id)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='products_calculated_metrics' AND COLUMN_NAME='task_id') THEN
        ALTER TABLE public.products_calculated_metrics ADD COLUMN task_id UUID REFERENCES public.analysis_tasks(id) ON DELETE CASCADE;
    END IF;
END $$;

-- 4. 考虑到 SKU 在不同任务中可能重复，我们需要将 (sku, task_id) 设为联合主键或移除主键约束。
-- 这里我们先简单处理：让 SKU 依然是主键，但如果是新任务，我们就更新它。或者更好的是移除旧的约束。
"""

print("哥，正在为您准备数据库升级脚本...")
with open("d:/item/ProSourcing/update_schema.sql", "w", encoding="utf-8") as f:
    f.write(migration_sql)

print("SQL 脚本已生成到 d:/item/ProSourcing/update_schema.sql")
print("由于 API Key 权限限制，请您在 Supabase SQL Editor 中直接运行该脚本。")
