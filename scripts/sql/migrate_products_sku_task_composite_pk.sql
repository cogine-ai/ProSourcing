-- Migrate products tables to composite (sku, task_id) keys.
-- Required for core/rpa_final_pipeline.py ON CONFLICT (sku, task_id) upserts (PR #55 / May 2026).

BEGIN;

-- Drop legacy single-column foreign key before changing primary keys.
ALTER TABLE public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_sku_fkey;

ALTER TABLE public.products_raw_data
    DROP CONSTRAINT IF EXISTS products_raw_data_pkey;

ALTER TABLE public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_pkey;

-- Rows without task_id cannot participate in the composite key; remove them.
DELETE FROM public.products_calculated_metrics WHERE task_id IS NULL;
DELETE FROM public.products_raw_data WHERE task_id IS NULL;

ALTER TABLE public.products_raw_data
    ALTER COLUMN task_id SET NOT NULL;

ALTER TABLE public.products_calculated_metrics
    ALTER COLUMN task_id SET NOT NULL;

ALTER TABLE public.products_raw_data
    ADD CONSTRAINT products_raw_data_pkey PRIMARY KEY (sku, task_id);

ALTER TABLE public.products_calculated_metrics
    ADD CONSTRAINT products_calculated_metrics_pkey PRIMARY KEY (sku, task_id);

ALTER TABLE public.products_calculated_metrics
    ADD CONSTRAINT products_calculated_metrics_sku_task_fkey
    FOREIGN KEY (sku, task_id)
    REFERENCES public.products_raw_data (sku, task_id)
    ON DELETE CASCADE;

COMMIT;
