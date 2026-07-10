-- Migrate product tables to composite primary key (sku, task_id).
-- Required by core/rpa_final_pipeline.py ON CONFLICT (sku, task_id) upserts.

BEGIN;

-- Remove rows that cannot participate in a composite key.
DELETE FROM public.products_calculated_metrics WHERE task_id IS NULL;
DELETE FROM public.products_raw_data WHERE task_id IS NULL;

ALTER TABLE public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_sku_fkey;

ALTER TABLE public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_pkey;

ALTER TABLE public.products_raw_data
    DROP CONSTRAINT IF EXISTS products_raw_data_pkey;

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
