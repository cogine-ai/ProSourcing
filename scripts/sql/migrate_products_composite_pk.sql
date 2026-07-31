-- Migrate products tables from sku-only PK to (sku, task_id) composite PK.
-- Required after commit a1f3d43 switched production upserts to ON CONFLICT (sku, task_id).

BEGIN;

-- Ensure task_id column exists on legacy databases.
ALTER TABLE public.products_raw_data ADD COLUMN IF NOT EXISTS task_id UUID;
ALTER TABLE public.products_calculated_metrics ADD COLUMN IF NOT EXISTS task_id UUID;

-- Orphan rows cannot participate in a composite primary key.
DELETE FROM public.products_calculated_metrics WHERE task_id IS NULL;
DELETE FROM public.products_raw_data WHERE task_id IS NULL;

ALTER TABLE public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_sku_fkey;

ALTER TABLE public.products_raw_data
    DROP CONSTRAINT IF EXISTS products_raw_data_pkey;

ALTER TABLE public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_pkey;

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
