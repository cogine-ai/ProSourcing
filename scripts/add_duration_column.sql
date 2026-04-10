-- 哥，刚那个 SQL 在 PowerShell 管道里可能解析出岔子了，我给它精简成一整行，防止换行符捣乱
ALTER TABLE analysis_tasks ADD COLUMN IF NOT EXISTS duration TEXT;

UPDATE analysis_tasks SET status = 'completed', progress = 100, error_msg = NULL WHERE status = 'failed' AND error_msg ILIKE '%duration%';
