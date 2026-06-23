-- Optional migration: move products_raw_data / products_calculated_metrics
-- from sku-only primary keys to composite (sku, task_id).
-- Run only after backing up data and updating application code to use the composite target.

BEGIN;

ALTER TABLE public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_sku_fkey;

ALTER TABLE public.products_raw_data
    DROP CONSTRAINT IF EXISTS products_raw_data_pkey;

ALTER TABLE public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_pkey;

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
