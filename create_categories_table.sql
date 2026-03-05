-- 创建 categories 表，用于存储品类统计数据
CREATE TABLE IF NOT EXISTS public.categories (
    category_id TEXT PRIMARY KEY,
    category_name TEXT NOT NULL,
    monthly_sales INTEGER DEFAULT 0,
    sale_amount NUMERIC DEFAULT 0,
    sale_product_qty INTEGER DEFAULT 0,
    is_has_subcategory INTEGER DEFAULT 1,
    amount_change_prc NUMERIC DEFAULT 0,
    restrict_type INTEGER DEFAULT 0,
    is_top_level BOOLEAN DEFAULT FALSE,
    parent_category_id TEXT,
    last_sync_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 安全策略
ALTER TABLE public.categories ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable Read All" ON public.categories FOR SELECT USING (true);
CREATE POLICY "Enable Insert/Update All" ON public.categories FOR ALL USING (true) WITH CHECK (true);
