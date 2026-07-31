-- Migrate products_raw_data / products_calculated_metrics to composite (sku, task_id) keys.
-- Required for RPA upserts that use ON CONFLICT (sku, task_id).

BEGIN;

-- Backfill missing task_id values before enforcing NOT NULL / composite PK.
UPDATE public.products_raw_data
SET task_id = '00000000-0000-0000-0000-000000000001'::uuid
WHERE task_id IS NULL;

UPDATE public.products_calculated_metrics pcm
SET task_id = prd.task_id
FROM public.products_raw_data prd
WHERE pcm.sku = prd.sku
  AND pcm.task_id IS NULL;

UPDATE public.products_calculated_metrics
SET task_id = '00000000-0000-0000-0000-000000000001'::uuid
WHERE task_id IS NULL;

ALTER TABLE public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_sku_fkey;

ALTER TABLE public.products_raw_data
    DROP CONSTRAINT IF EXISTS products_raw_data_pkey;

ALTER TABLE public.products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_pkey;

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
