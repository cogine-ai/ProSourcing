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
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS leaf_count INTEGER DEFAULT 0;
