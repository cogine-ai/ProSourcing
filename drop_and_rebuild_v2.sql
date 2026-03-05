-- =======================================================
-- ProSourcing 数据表全量重建 SQL (v2.0 工业级全字段版)
-- 哥，这一版把接口里 40 多个字段全铺开了，请在 Supabase SQL Editor 直接执行。
-- =======================================================

-- 1. 彻底清理旧资产
DROP TABLE IF EXISTS public.products_calculated_metrics CASCADE;
DROP TABLE IF EXISTS public.products_raw_data CASCADE;
DROP TABLE IF EXISTS public.analysis_tasks CASCADE;

-- 2. 重建【任务司令部】 (analysis_tasks)
CREATE TABLE public.analysis_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,                   -- 哥选的品类名
    status TEXT DEFAULT 'pending',            -- 状态
    progress INTEGER DEFAULT 0,
    category_id TEXT,                         -- 类目 ID (如 00002)
    category_stats JSONB,                     -- 存接口 2 的全盘统计 (sale_qty, sale_amount 等)
    trend_data JSONB,                         -- 存接口 6 的 6 个月趋势折线数据
    up_categories JSONB,                      -- 存层级路径 (用于面包屑显示)
    excel_path TEXT,
    error_msg TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. 重建【原始数据仓】 (products_raw_data)
CREATE TABLE public.products_raw_data (
    sku TEXT PRIMARY KEY,                     -- 对应 product_code
    task_id UUID REFERENCES public.analysis_tasks(id) ON DELETE CASCADE,
    
    -- 核心业务字段 (全对齐 接口.txt)
    product_name TEXT,
    gen_brand_id BIGINT,
    brand_name TEXT,
    product_url TEXT,
    sale_price NUMERIC,
    product_rate NUMERIC,
    review_qty INTEGER,
    merchant_count INTEGER,
    sale_qty INTEGER,                        -- 月销售数量
    sale_amount NUMERIC,                     -- 月销售额
    last_sale_date DATE,
    created_dt TIMESTAMP,                    -- 上架日期
    amount_prc NUMERIC,                      -- 销售额占比
    amount_abc INTEGER,                      -- ABC 分级 (1, 2, 3)
    
    -- 多维扩展
    preview_image_list JSONB,                -- 存储各种尺寸图片 URL 列表
    category_name TEXT,                      -- 类目名称
    category_ext_id TEXT,                    -- 类目扩展 ID
    restrict_type INTEGER,                   -- 限制类型
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. 重建【算法得分仓】 (products_calculated_metrics)
CREATE TABLE public.products_calculated_metrics (
    sku TEXT PRIMARY KEY REFERENCES public.products_raw_data(sku) ON DELETE CASCADE,
    task_id UUID REFERENCES public.analysis_tasks(id) ON DELETE CASCADE,
    
    total_score NUMERIC DEFAULT 0,           -- 总分
    cr3_ratio NUMERIC DEFAULT 0,             -- 集中度计算值
    notes TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. 极速读写授权 (RLS)
ALTER TABLE public.analysis_tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public Access" ON public.analysis_tasks FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.products_raw_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public Access" ON public.products_raw_data FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.products_calculated_metrics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public Access" ON public.products_calculated_metrics FOR ALL USING (true) WITH CHECK (true);

-- 哥，SQL 准备就绪，跑完这些，表就彻底变“全能”了！
