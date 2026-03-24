-- ProSourcing 生产环境 PostgreSQL 初始化脚本

-- 1. 原始数据表
CREATE TABLE IF NOT EXISTS products_raw_data (
    sku TEXT PRIMARY KEY,
    task_id UUID,
    product_name TEXT,
    brand_name TEXT,
    gen_brand_id TEXT,
    product_url TEXT,
    sale_price NUMERIC,
    product_rate NUMERIC,
    review_qty INTEGER,
    merchant_count INTEGER,
    sale_qty INTEGER,
    sale_amount NUMERIC,
    amount_abc TEXT,
    amount_prc NUMERIC,
    preview_image_list JSONB,
    created_dt TIMESTAMP,
    category_name TEXT,
    category_ext_id TEXT,
    restrict_type TEXT,
    last_sale_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. 指标计算结果表
CREATE TABLE IF NOT EXISTS products_calculated_metrics (
    sku TEXT PRIMARY KEY REFERENCES products_raw_data(sku) ON DELETE CASCADE,
    task_id UUID,
    total_score NUMERIC,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. 任务分析主表
CREATE TABLE IF NOT EXISTS analysis_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT,
    status TEXT,
    progress INTEGER DEFAULT 0,
    error_msg TEXT,
    excel_path TEXT,
    duration TEXT,
    category_id TEXT,
    category_stats JSONB,
    trend_data JSONB,
    up_categories JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. 核心类目字典表 (Master)
CREATE TABLE IF NOT EXISTS algatop_categories_master (
    algatop_id TEXT PRIMARY KEY,
    name_ru TEXT,
    name_cn TEXT,
    name_en TEXT,
    parent_id TEXT,
    level INTEGER,
    is_leaf BOOLEAN,
    monthly_sales BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. 一级大类顶部统计表
CREATE TABLE IF NOT EXISTS algatop_top_category_stats (
    algatop_id TEXT PRIMARY KEY,
    sales_qty BIGINT DEFAULT 0,
    revenue BIGINT DEFAULT 0,
    product_count BIGINT DEFAULT 0,
    seller_count BIGINT DEFAULT 0,
    brand_count BIGINT DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 6. 算法策略配置表
CREATE TABLE IF NOT EXISTS algorithm_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    config_json JSONB,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_raw_task_id ON products_raw_data(task_id);
CREATE INDEX IF NOT EXISTS idx_calc_task_id ON products_calculated_metrics(task_id);
CREATE INDEX IF NOT EXISTS idx_master_parent ON algatop_categories_master(parent_id);
CREATE INDEX IF NOT EXISTS idx_master_level ON algatop_categories_master(level);
