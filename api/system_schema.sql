-- =======================================================
-- 系统管理功能扩展：用户与设置表
-- =======================================================

-- 1. 系统用户表
CREATE TABLE IF NOT EXISTS public.system_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'analyst', -- admin, analyst
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. 系统设置表 (KeyValue 结构)
CREATE TABLE IF NOT EXISTS public.system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. 初始索引与权限
ALTER TABLE public.system_users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public Access Users" ON public.system_users FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.system_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public Access Settings" ON public.system_settings FOR ALL USING (true) WITH CHECK (true);

-- 4. 插入默认配置
INSERT INTO public.system_settings (key, value, description)
VALUES 
    ('storage_config', '{"path": "./output", "auto_cleanup_days": 15}', '文件存储相关配置'),
    ('collection_config', '{"algatop": {"username": "", "password": ""}}', '数据平台采集凭据')
ON CONFLICT (key) DO NOTHING;

-- 5. 插入默认管理员 (初始密码: admin123, 建议生产环境修改)
INSERT INTO public.system_users (username, password_hash, role)
VALUES ('admin', 'admin123', 'admin')
ON CONFLICT (username) DO NOTHING;
