-- Migrate products tables from sku-only PK to (sku, task_id) composite PK.
-- Run once in production before switching the default upsert target.

BEGIN;

DELETE FROM products_calculated_metrics
WHERE task_id IS NULL
   OR sku IN (SELECT sku FROM products_raw_data WHERE task_id IS NULL);

DELETE FROM products_raw_data
WHERE task_id IS NULL;

ALTER TABLE products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_sku_fkey;

ALTER TABLE products_calculated_metrics
    DROP CONSTRAINT IF EXISTS products_calculated_metrics_pkey;

ALTER TABLE products_raw_data
    DROP CONSTRAINT IF EXISTS products_raw_data_pkey;

ALTER TABLE products_raw_data
    ALTER COLUMN task_id SET NOT NULL;

ALTER TABLE products_calculated_metrics
    ALTER COLUMN task_id SET NOT NULL;

ALTER TABLE products_raw_data
    ADD CONSTRAINT products_raw_data_pkey PRIMARY KEY (sku, task_id);

ALTER TABLE products_calculated_metrics
    ADD CONSTRAINT products_calculated_metrics_pkey PRIMARY KEY (sku, task_id);

ALTER TABLE products_calculated_metrics
    ADD CONSTRAINT products_calculated_metrics_sku_task_id_fkey
    FOREIGN KEY (sku, task_id)
    REFERENCES products_raw_data (sku, task_id)
    ON DELETE CASCADE;

COMMIT;
