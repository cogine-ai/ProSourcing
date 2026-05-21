# ProSourcing 现场部署手册

## 1. 本次变更内容

- 前端发起任务时，直接把一级分类信息一起提交给后端。
- 后端在创建任务时，把一级分类信息写入 `analysis_tasks`。
- 任务列表直接读取 `analysis_tasks.top_category_name_cn`，不再在 `/api/tasks/history` 中逐条补算一级分类。
- 数据库不再要求重新制作数据库镜像；客户现场直接在 Docker 数据库里执行升级 SQL。

---

## 2. 需要更新的文件

### 后端

- `api/server.py`

### 前端

- `frontend_pro/src/App.jsx`
- `frontend_pro/src/components/KaspiTaskView.jsx`

### 数据库 SQL

- `scripts/sql/add_top_category_columns.sql`
- `scripts/sql/backfill_task_top_category.sql`

---

## 3. 重新打包前后端镜像

在项目根目录执行：

```powershell
docker build -f Dockerfile.frontend -t prosourcing-frontend:20260402 .
docker save prosourcing-frontend:20260402 -o deployment_package/20260402/prosourcing-frontend_20260402.tar

docker build -f Dockerfile.backend -t prosourcing-backend:20260402 .
docker save prosourcing-backend:20260402 -o deployment_package/20260402/prosourcing-backend_20260402.tar
```

拷贝以下文件到客户现场：

- `deployment_package/20260402/prosourcing-frontend_20260402.tar`
- `deployment_package/20260402/prosourcing-backend_20260402.tar`
- `deployment_package/20260402/docker-compose.yml`
- `scripts/sql/add_top_category_columns.sql`
- `scripts/sql/backfill_task_top_category.sql`

---

## 4. 客户现场升级步骤

### 4.1 导入新镜像

```powershell
docker load -i prosourcing-frontend_20260402.tar
docker load -i prosourcing-backend_20260402.tar
```

### 4.2 重启前后端容器

在 `docker-compose.yml` 所在目录执行：

```powershell
docker compose up -d frontend backend
```

---

## 5. 数据库升级步骤

### 5.1 进入数据库

```powershell
docker exec -it prosourcing_db psql -U postgres -d prosourcing
```

### 5.2 执行商品表联合主键迁移（2026-05-17 之后后端必需）

若 RPA 报告阶段报错 `there is no unique or exclusion constraint matching the ON CONFLICT specification`，说明数据库仍是旧的 `sku` 单主键。请执行：

```powershell
Get-Content scripts/sql/migrate_products_sku_task_composite_pk.sql | docker exec -i prosourcing_db psql -U postgres -d prosourcing
```

### 5.3 执行加字段 SQL

把 `scripts/sql/add_top_category_columns.sql` 内容粘贴进去执行：

```sql
ALTER TABLE public.analysis_tasks
    ADD COLUMN IF NOT EXISTS top_category_id TEXT,
    ADD COLUMN IF NOT EXISTS top_category_name_cn TEXT,
    ADD COLUMN IF NOT EXISTS top_category_name_ru TEXT;

CREATE INDEX IF NOT EXISTS idx_tasks_top_category_name_cn
    ON public.analysis_tasks(top_category_name_cn);
```

### 5.4 回填历史任务一级分类

把 `scripts/sql/backfill_task_top_category.sql` 内容粘贴进去执行：

```sql
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
```

### 5.5 退出数据库

```sql
\q
```

---

## 6. 升级后验证

### 6.1 检查字段是否存在

```powershell
docker exec -it prosourcing_db psql -U postgres -d prosourcing -c "\d analysis_tasks"
```

应能看到：

- `top_category_id`
- `top_category_name_cn`
- `top_category_name_ru`

### 6.2 检查历史任务是否回填成功

```powershell
docker exec -it prosourcing_db psql -U postgres -d prosourcing -c "SELECT id, category, top_category_name_cn FROM analysis_tasks ORDER BY created_at DESC LIMIT 10;"
```

### 6.3 检查接口

```powershell
curl http://localhost:8000/api/tasks/history?page=1&page_size=5
```

返回结果中应能看到 `top_category_name_cn`。

---

## 7. 中断任务恢复

如果系统更新后有任务卡在中间状态，先把脚本拷进后端容器：

```powershell
docker cp recover_interrupted_tasks.py prosourcing_backend:/app/recover_interrupted_tasks.py
```

然后执行：

```powershell
docker exec -it prosourcing_backend python /app/recover_interrupted_tasks.py --stale-minutes 30 --dry-run
docker exec -it prosourcing_backend python /app/recover_interrupted_tasks.py --stale-minutes 30
```

---

## 8. 注意事项

- 这次升级不需要替换数据库镜像。
- 如果客户现场数据库已经有旧数据，一定要执行第 5 节 SQL。
- 如果前端列表还是旧的一级分类显示，先刷新页面，再检查第 5.3 步是否执行成功。
