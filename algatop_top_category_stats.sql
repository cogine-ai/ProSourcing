-- 创建一级大类顶部统计表
CREATE TABLE IF NOT EXISTS public.algatop_top_category_stats (
    algatop_id TEXT PRIMARY KEY,
    sales_qty BIGINT DEFAULT 0,
    revenue BIGINT DEFAULT 0,
    product_count BIGINT DEFAULT 0,
    seller_count BIGINT DEFAULT 0,
    brand_count BIGINT DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);
