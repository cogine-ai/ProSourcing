CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.products_raw_data (
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
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.products_calculated_metrics (
    sku TEXT PRIMARY KEY REFERENCES public.products_raw_data(sku) ON DELETE CASCADE,
    task_id UUID,
    total_score NUMERIC,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.analysis_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT,
    status TEXT DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    error_msg TEXT,
    excel_path TEXT,
    duration TEXT,
    category_id TEXT,
    category_stats JSONB,
    trend_data JSONB,
    up_categories JSONB,
    top_category_id TEXT,
    top_category_name_cn TEXT,
    top_category_name_ru TEXT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.algatop_categories_master (
    algatop_id TEXT PRIMARY KEY,
    name_ru TEXT,
    name_cn TEXT,
    name_en TEXT,
    parent_id TEXT,
    level INTEGER,
    is_leaf BOOLEAN DEFAULT FALSE,
    monthly_sales BIGINT DEFAULT 0,
    last_crawl_date DATE,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.algatop_top_category_stats (
    algatop_id TEXT PRIMARY KEY,
    sales_qty BIGINT DEFAULT 0,
    revenue BIGINT DEFAULT 0,
    product_count BIGINT DEFAULT 0,
    seller_count BIGINT DEFAULT 0,
    brand_count BIGINT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.algorithm_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    config_json JSONB,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.system_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'analyst',
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.categories (
    category_id TEXT PRIMARY KEY,
    category_name TEXT,
    parent_category_id TEXT,
    monthly_sales BIGINT DEFAULT 0,
    sale_product_qty BIGINT DEFAULT 0,
    sale_qty BIGINT DEFAULT 0,
    leaf_count INTEGER DEFAULT 0,
    algatop_id TEXT,
    name_ru TEXT,
    name_cn TEXT,
    name_en TEXT,
    level INTEGER,
    is_leaf BOOLEAN DEFAULT FALSE,
    is_top_level BOOLEAN DEFAULT FALSE,
    is_has_subcategory INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.category_last_crawl_dates (
    category_code TEXT PRIMARY KEY,
    last_crawl_date DATE NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.global_category_dict (
    algatop_id TEXT PRIMARY KEY,
    kaspi_id TEXT,
    parent_algatop_id TEXT,
    category_name TEXT,
    name_ru TEXT,
    name_cn TEXT,
    name_en TEXT,
    is_top_level BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.analysis_tasks_category_id_backup (
    id UUID PRIMARY KEY,
    old_category_id TEXT,
    category TEXT,
    backed_up_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

ALTER TABLE public.products_raw_data ADD COLUMN IF NOT EXISTS task_id UUID;
ALTER TABLE public.products_raw_data ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now());
ALTER TABLE public.products_raw_data ADD COLUMN IF NOT EXISTS category_name TEXT;
ALTER TABLE public.products_raw_data ADD COLUMN IF NOT EXISTS category_ext_id TEXT;
ALTER TABLE public.products_raw_data ADD COLUMN IF NOT EXISTS restrict_type TEXT;
ALTER TABLE public.products_raw_data ADD COLUMN IF NOT EXISTS last_sale_date DATE;

ALTER TABLE public.products_calculated_metrics ADD COLUMN IF NOT EXISTS task_id UUID;
ALTER TABLE public.products_calculated_metrics ADD COLUMN IF NOT EXISTS total_score NUMERIC;
ALTER TABLE public.products_calculated_metrics ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now());

ALTER TABLE public.analysis_tasks ADD COLUMN IF NOT EXISTS error_msg TEXT;
ALTER TABLE public.analysis_tasks ADD COLUMN IF NOT EXISTS excel_path TEXT;
ALTER TABLE public.analysis_tasks ADD COLUMN IF NOT EXISTS duration TEXT;
ALTER TABLE public.analysis_tasks ADD COLUMN IF NOT EXISTS category_id TEXT;
ALTER TABLE public.analysis_tasks ADD COLUMN IF NOT EXISTS category_stats JSONB;
ALTER TABLE public.analysis_tasks ADD COLUMN IF NOT EXISTS trend_data JSONB;
ALTER TABLE public.analysis_tasks ADD COLUMN IF NOT EXISTS up_categories JSONB;
ALTER TABLE public.analysis_tasks ADD COLUMN IF NOT EXISTS top_category_id TEXT;
ALTER TABLE public.analysis_tasks ADD COLUMN IF NOT EXISTS top_category_name_cn TEXT;
ALTER TABLE public.analysis_tasks ADD COLUMN IF NOT EXISTS top_category_name_ru TEXT;
ALTER TABLE public.analysis_tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now());

ALTER TABLE public.algatop_categories_master ADD COLUMN IF NOT EXISTS name_cn TEXT;
ALTER TABLE public.algatop_categories_master ADD COLUMN IF NOT EXISTS name_en TEXT;
ALTER TABLE public.algatop_categories_master ADD COLUMN IF NOT EXISTS parent_id TEXT;
ALTER TABLE public.algatop_categories_master ADD COLUMN IF NOT EXISTS level INTEGER;
ALTER TABLE public.algatop_categories_master ADD COLUMN IF NOT EXISTS is_leaf BOOLEAN DEFAULT FALSE;
ALTER TABLE public.algatop_categories_master ADD COLUMN IF NOT EXISTS monthly_sales BIGINT DEFAULT 0;
ALTER TABLE public.algatop_categories_master ADD COLUMN IF NOT EXISTS last_crawl_date DATE;
ALTER TABLE public.algatop_categories_master ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now());
ALTER TABLE public.algatop_categories_master ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now());

ALTER TABLE public.algatop_top_category_stats ADD COLUMN IF NOT EXISTS sales_qty BIGINT DEFAULT 0;
ALTER TABLE public.algatop_top_category_stats ADD COLUMN IF NOT EXISTS revenue BIGINT DEFAULT 0;
ALTER TABLE public.algatop_top_category_stats ADD COLUMN IF NOT EXISTS product_count BIGINT DEFAULT 0;
ALTER TABLE public.algatop_top_category_stats ADD COLUMN IF NOT EXISTS seller_count BIGINT DEFAULT 0;
ALTER TABLE public.algatop_top_category_stats ADD COLUMN IF NOT EXISTS brand_count BIGINT DEFAULT 0;
ALTER TABLE public.algatop_top_category_stats ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now());

ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS category_name TEXT;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS parent_category_id TEXT;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS monthly_sales BIGINT DEFAULT 0;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS sale_product_qty BIGINT DEFAULT 0;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS sale_qty BIGINT DEFAULT 0;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS leaf_count INTEGER DEFAULT 0;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS algatop_id TEXT;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS name_ru TEXT;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS name_cn TEXT;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS name_en TEXT;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS level INTEGER;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS is_leaf BOOLEAN DEFAULT FALSE;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS is_top_level BOOLEAN DEFAULT FALSE;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS is_has_subcategory INTEGER DEFAULT 1;
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now());
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now());

CREATE INDEX IF NOT EXISTS idx_raw_task_id ON public.products_raw_data(task_id);
CREATE INDEX IF NOT EXISTS idx_calc_task_id ON public.products_calculated_metrics(task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON public.analysis_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_category_id ON public.analysis_tasks(category_id);
CREATE INDEX IF NOT EXISTS idx_tasks_top_category_name_cn ON public.analysis_tasks(top_category_name_cn);
CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON public.analysis_tasks(updated_at);
CREATE INDEX IF NOT EXISTS idx_master_parent ON public.algatop_categories_master(parent_id);
CREATE INDEX IF NOT EXISTS idx_master_level ON public.algatop_categories_master(level);
CREATE INDEX IF NOT EXISTS idx_master_name_ru ON public.algatop_categories_master(name_ru);
CREATE INDEX IF NOT EXISTS idx_master_name_cn ON public.algatop_categories_master(name_cn);
CREATE INDEX IF NOT EXISTS idx_categories_parent ON public.categories(parent_category_id);
CREATE INDEX IF NOT EXISTS idx_categories_algatop_id ON public.categories(algatop_id);
CREATE INDEX IF NOT EXISTS idx_categories_monthly_sales ON public.categories(monthly_sales);
CREATE INDEX IF NOT EXISTS idx_categories_name_ru ON public.categories(name_ru);
CREATE INDEX IF NOT EXISTS idx_categories_name_cn ON public.categories(name_cn);

INSERT INTO public.system_settings (key, value, description)
VALUES
    ('storage_config', '{"path": "./output", "auto_cleanup_days": 15}', 'Storage settings'),
    ('collection_config', '{"algatop": {"username": "", "password": ""}}', 'Algatop credentials')
ON CONFLICT (key) DO NOTHING;

INSERT INTO public.system_users (username, password_hash, role)
VALUES ('admin', 'admin123', 'admin')
ON CONFLICT (username) DO NOTHING;
