-- Migrate products tables to composite primary key (sku, task_id).
-- Required for per-task product rows when the same SKU appears in multiple analysis tasks.
-- Safe to run multiple times.

BEGIN;

-- Remove rows that cannot satisfy NOT NULL task_id before adding composite PK.
DELETE FROM public.products_calculated_metrics WHERE task_id IS NULL;
DELETE FROM public.products_raw_data WHERE task_id IS NULL;

ALTER TABLE public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_pkey;

ALTER TABLE public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_sku_fkey;

ALTER TABLE public.products_raw_data
    DROP CONSTRAINT IF EXISTS products_raw_data_pkey;

ALTER TABLE public.products_raw_data
    ALTER COLUMN task_id SET NOT NULL;

ALTER TABLE public.products_raw_data
    ADD CONSTRAINT products_raw_data_pkey PRIMARY KEY (sku, task_id);

ALTER TABLE public.products_calculated_metrics
    ALTER COLUMN task_id SET NOT NULL;

ALTER TABLE public.products_calculated_metrics
    ADD CONSTRAINT products_calculated_metrics_pkey PRIMARY KEY (sku, task_id);

ALTER TABLE public.products_calculated_metrics
    ADD CONSTRAINT products_calculated_metrics_sku_task_fkey
    FOREIGN KEY (sku, task_id)
    REFERENCES public.products_raw_data (sku, task_id)
    ON DELETE CASCADE;

COMMIT;
