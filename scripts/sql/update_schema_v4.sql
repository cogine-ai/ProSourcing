-- 哥，这是第4版数据库补丁：增加任务耗时字段
ALTER TABLE analysis_tasks ADD COLUMN IF NOT EXISTS duration INTEGER;
