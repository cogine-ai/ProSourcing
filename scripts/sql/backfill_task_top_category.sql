WITH RECURSIVE lineage AS (
    SELECT
        t.id AS task_id,
        m.algatop_id,
        m.parent_id,
        m.name_cn,
        m.name_ru,
        0 AS depth
    FROM public.analysis_tasks t
    JOIN public.algatop_categories_master m
      ON m.algatop_id::text = t.category_id::text
    WHERE COALESCE(t.category_id, '') <> ''

    UNION ALL

    SELECT
        l.task_id,
        parent.algatop_id,
        parent.parent_id,
        parent.name_cn,
        parent.name_ru,
        l.depth + 1
    FROM lineage l
    JOIN public.algatop_categories_master parent
      ON parent.algatop_id::text = l.parent_id::text
    WHERE COALESCE(l.parent_id, '') <> ''
),
top_level AS (
    SELECT DISTINCT ON (task_id)
        task_id,
        algatop_id,
        name_cn,
        name_ru
    FROM lineage
    ORDER BY task_id, depth DESC
)
UPDATE public.analysis_tasks t
SET top_category_id = top_level.algatop_id::text,
    top_category_name_cn = top_level.name_cn,
    top_category_name_ru = top_level.name_ru
FROM top_level
WHERE t.id = top_level.task_id
  AND (
      COALESCE(t.top_category_id, '') = ''
      OR COALESCE(t.top_category_name_cn, '') = ''
  );
