-- =======================================================
-- ProSourcing 数据库字段补充 SQL (v3.0 更新现场反馈)
-- 说明：增加 updated_at 字段，用于精准记录任务执行的完成及最新变动时间
-- =======================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='analysis_tasks' AND COLUMN_NAME='updated_at') THEN
        ALTER TABLE public.analysis_tasks ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now());
    END IF;
END $$;
