-- v5: allow the same SKU to belong to different analysis tasks without upsert failures.
-- Run once on production PostgreSQL (docker-compose ENV_MOD=production).

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.products_raw_data'::regclass
          AND contype = 'p'
          AND pg_get_constraintdef(oid) LIKE '%sku, task_id%'
    ) THEN
        ALTER TABLE public.products_calculated_metrics
            DROP CONSTRAINT IF EXISTS products_calculated_metrics_sku_fkey;

        ALTER TABLE public.products_calculated_metrics
            DROP CONSTRAINT IF EXISTS products_calculated_metrics_pkey;

        ALTER TABLE public.products_raw_data
            DROP CONSTRAINT IF EXISTS products_raw_data_pkey;

        ALTER TABLE public.products_raw_data
            ADD PRIMARY KEY (sku, task_id);

        ALTER TABLE public.products_calculated_metrics
            ADD PRIMARY KEY (sku, task_id);

        ALTER TABLE public.products_calculated_metrics
            ADD CONSTRAINT products_calculated_metrics_sku_task_fkey
            FOREIGN KEY (sku, task_id)
            REFERENCES public.products_raw_data (sku, task_id)
            ON DELETE CASCADE;
    END IF;
END $$;
