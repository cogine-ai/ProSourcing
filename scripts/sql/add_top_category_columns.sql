ALTER TABLE public.analysis_tasks
    ADD COLUMN IF NOT EXISTS top_category_id TEXT,
    ADD COLUMN IF NOT EXISTS top_category_name_cn TEXT,
    ADD COLUMN IF NOT EXISTS top_category_name_ru TEXT;

CREATE INDEX IF NOT EXISTS idx_tasks_top_category_name_cn
    ON public.analysis_tasks(top_category_name_cn);
