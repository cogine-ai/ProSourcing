-- Migrate products_raw_data / products_calculated_metrics to composite (sku, task_id) PK.
-- Required for production RPA upserts using ON CONFLICT (sku, task_id).
-- Safe to run multiple times (uses IF EXISTS guards).

BEGIN;

-- Drop FK from metrics -> raw (sku-only)
ALTER TABLE IF EXISTS public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_sku_fkey;

-- Drop single-column primary keys
ALTER TABLE IF EXISTS public.products_raw_data
    DROP CONSTRAINT IF EXISTS products_raw_data_pkey;

ALTER TABLE IF EXISTS public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_pkey;

-- Rows without task_id cannot participate in composite PK; remove orphans.
DELETE FROM public.products_calculated_metrics WHERE task_id IS NULL;
DELETE FROM public.products_raw_data WHERE task_id IS NULL;

ALTER TABLE public.products_raw_data
    ALTER COLUMN task_id SET NOT NULL;

ALTER TABLE public.products_calculated_metrics
    ALTER COLUMN task_id SET NOT NULL;

-- Deduplicate before adding composite PK (keep newest by updated_at / created_at)
DELETE FROM public.products_raw_data a
    USING public.products_raw_data b
WHERE a.sku = b.sku
  AND a.task_id = b.task_id
  AND a.ctid < b.ctid;

DELETE FROM public.products_calculated_metrics a
    USING public.products_calculated_metrics b
WHERE a.sku = b.sku
  AND a.task_id = b.task_id
  AND a.ctid < b.ctid;

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
