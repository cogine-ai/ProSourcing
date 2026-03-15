# ProSourcing - AI 选品分析系统

哥，这是一个集成了 RPA 采集、潜力评分算法和可视化报表的完整系统。

## 🚀 快速启动

你可以通过以下命令一键启动后端（FastAPI）和前端（Vite）：

```powershell
python run_dev.py
```

## 🛠️ 核心工作流

1. **RPA 采集**：
   运行 RPA 脚本抓取 Algatop 数据。
   ```powershell
   python core/algatop_rpa_scraper.py [类目代码]
   ```
   *默认类目为 04456 (儿童交通)*

2. **数据入库与评分**：
   将抓取的本地 JSON 同步到 Supabase 数据库并生成 Excel 报告。
   ```powershell
   python core/rpa_final_pipeline.py
   ```

## 📂 目录结构 

- `api/`: 后端服务代码 (FastAPI)
- `frontend_pro/`: 前端项目代码 (Vite + React)
- `core/`: 核心业务逻辑 (Scraper, Pipeline, Scoring)
- `output/`: 统一产出目录
  - `excel/`: 最终生成的分析报表 (.xlsx)
  - `json/`: 采集过程中的原始数据 (.json)
  - `images/`: 商品首图缓存 (.jpg)
- `tests/`: 脚本库 (安置 100+ 调试、诊断和测试脚本，干净清爽)
  - `debug/`: 调试类
  - `tools/`: 工具与提取类
  - (根目录下为原有测试脚本)
- `templates/`: 模板文件 (如 Excel 导出模板)
- `docs/`: 项目文档 (部署指南、SOP 等)

## 🔧 环境配置

请确保根目录下有 `.env` 文件，包含以下配置：
- `ALGATOP_USER`: 账号
- `ALGATOP_PASS`: 密码
- `SUPABASE_URL`: 数据库地址
- `SUPABASE_KEY`: 数据库秘钥

## 🗄️ 数据库环境分流 (哥，看这里)

系统通过 `ENV_MOD` 环境变量实现数据库的“一键切流”，逻辑位于 `core/final_pipeline.py`：

1.  **生产环境 (Docker 模式)**：
    -   **开关**：`ENV_MOD=production` (已在 `docker-compose.yml` 中默认配置)
    -   **数据库**：使用 Docker 内部部署的 **PostgreSQL**。
    -   **连接串**：由 `DATABASE_URL` 指定。
    -   **特点**：数据全量存储在本地卷 `pgdata` 中，不依赖云端。

2.  **开发环境 (Local 模式)**：
    -   **开关**：`ENV_MOD=development` (默认值)
    -   **数据库**：连接 **Supabase 云端**。
    -   **配置**：从 `.env` 读取 `SUPABASE_URL` 和 `SUPABASE_KEY`。

> [!IMPORTANT]
> **写入数据的归宿**：如果您在生产环境运行（Docker 中），数据会进入容器内的 PG；如果您在本地直接 `python` 运行脚本且没设环境变量，数据会尝试同步到 Supabase。
