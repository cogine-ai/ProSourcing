-- =======================================================
-- AI 选品分析 Agent: 数据库及存储池初始化 SQL
-- 基于最新 template.xlsx “原始数据仓” + “指标计算仓” 双层架构
-- =======================================================

-- 一、创建核心选品原始数据表 (参照 excel 中 Sheet: '原始数据')
-- 您或其他爬虫/人工仅需将这里的信息填充满，后续 Python 将直接读取这里并测算出分析结果
CREATE TABLE public.products_raw_data (
    -- 对应 Sheet '原始数据' 列头
    sku TEXT PRIMARY KEY,                       -- SKU (主键)
    product_name TEXT,                          -- 产品名称
    listing_date DATE,                          -- 上架时间 (Появилось в Каспи 等)
    brand TEXT,                                 -- 品牌
    rating NUMERIC,                             -- 分级/评分
    reviews_count INTEGER DEFAULT 0,            -- 评论
    sellers INTEGER DEFAULT 0,                  -- 卖家
    price NUMERIC,                              -- 价格
    weight TEXT,                                -- Bec (重量)
    commission TEXT,                            -- 佣金
    product_url TEXT,                           -- 产品链接
    sales_3m INTEGER DEFAULT 0,                 -- 近3个月销量数
    revenue_3m NUMERIC DEFAULT 0,               -- 近3个月的销售收入
    
    -- 以下是用于计算 Sheet1 大盘指标所需的隐藏核心依据
    category_tree TEXT,                         -- 产品类目树
    category_total_sales INTEGER DEFAULT 0,     -- 该商品所属细分类目总销量
    category_total_products INTEGER DEFAULT 0,  -- 该商品所属细分类目总商品数
    top3_sales_sum INTEGER DEFAULT 0,           -- 该细分类目下前 3 名的月销量总和 (计算 CR3 用)
    
    -- 媒体外链 / Storage 存储直链
    image_url TEXT,                             -- 产品首图 (可直填 URL 或我们在 Storage 生成)
    chart_url TEXT,                             -- 细分类目销量曲线图
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 二、创建指标计算分析结果表 (参照 excel 中 Sheet: '指标计算分析')
-- 这个表不需要您用其他工具抓取填充！我们将用 Python 从上一张表拿取原始数据，自动计算全部得分项后写回到本表。
CREATE TABLE public.products_calculated_metrics (
    sku TEXT PRIMARY KEY REFERENCES public.products_raw_data(sku) ON DELETE CASCADE,
    file_generation_time TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    
    -- 明确带“得分”和其他算分项的列
    monthly_sales_score NUMERIC DEFAULT 0,          -- 月销数量得分
    reviews_score NUMERIC DEFAULT 0,                -- 评论数量得分
    price_score NUMERIC DEFAULT 0,                  -- 产品售价得分
    sales_to_products_ratio NUMERIC DEFAULT 0,      -- 月销/细分类目总数比值
    days_to_reviews_ratio NUMERIC DEFAULT 0,        -- 距离时间天数/评论数比值
    cr3_ratio NUMERIC DEFAULT 0,                    -- CR3 集中度比例
    total_score NUMERIC DEFAULT 0,                  -- 得分总和
    notes TEXT,                                     -- 备注
    
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 三、安全策略 (Row Level Security) - 允许读取与快捷写入
ALTER TABLE public.products_raw_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable Read Raw" ON public.products_raw_data FOR SELECT USING (true);
CREATE POLICY "Enable Insert Raw" ON public.products_raw_data FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable Update Raw" ON public.products_raw_data FOR UPDATE USING (true);

ALTER TABLE public.products_calculated_metrics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable Read Calc" ON public.products_calculated_metrics FOR SELECT USING (true);
CREATE POLICY "Enable Insert Calc" ON public.products_calculated_metrics FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable Update Calc" ON public.products_calculated_metrics FOR UPDATE USING (true);

-- =======================================================
-- 四、初始化 Supabase Storage 存储桶 (存放首图和折线图图表)
-- =======================================================

INSERT INTO storage.buckets (id, name, public) 
VALUES ('product-images', 'product-images', true)
ON CONFLICT (id) DO NOTHING;

-- 极简公共授权
CREATE POLICY "Public Read Img" ON storage.objects FOR SELECT USING (bucket_id = 'product-images');
CREATE POLICY "Public Insert Img" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'product-images');
CREATE POLICY "Public Update Img" ON storage.objects FOR UPDATE USING (bucket_id = 'product-images');
CREATE POLICY "Public Delete Img" ON storage.objects FOR DELETE USING (bucket_id = 'product-images');
