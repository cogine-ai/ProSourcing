<div align="center">
  <img src="./assets/logo.png" width="120" height="120" alt="ProSourcing Logo" />
  <h1>ProSourcing</h1>
  <p><b>AI-Powered Product Sourcing & Analytics System</b></p>
  <p><i>高效的一键式 AI 选品与分析解决方案</i></p>

  <p>
    <img src="https://img.shields.io/github/license/cogine-ai/ProSourcing?style=for-the-badge&color=blue" alt="license" />
    <img src="https://img.shields.io/github/v/release/cogine-ai/ProSourcing?style=for-the-badge&color=green" alt="version" />
    <img src="https://img.shields.io/github/last-commit/cogine-ai/ProSourcing?style=for-the-badge" alt="last commit" />
    <img src="https://img.shields.io/github/repo-size/cogine-ai/ProSourcing?style=for-the-badge" alt="repo size" />
  </p>

  <p>
    <a href="#english">English</a> | 
    <a href="#中文">中文</a>
  </p>
</div>

---

<h2 id="english">🌐 English</h2>

### Introduction
**ProSourcing** is a comprehensive product sourcing system that integrates RPA data collection, potential scoring algorithms, and interactive visual reports. Designed to streamline the transition from raw marketplace data to actionable business insights.

### 🚀 Quick Start
Launch both the backend (FastAPI) and frontend (Vite) with a single command:
```powershell
python run_dev.py
```

### 🛠️ Core Workflows
1.  **RPA Scraper**: Crawl data from Algatop.
    ```powershell
    python core/algatop_rpa_scraper.py [category_code]
    ```
2.  **Pipeline & Analytics**: Sync JSON to Supabase and generate Excel reports.
    ```powershell
    python core/rpa_final_pipeline.py
    ```

### 📂 Project Structure
- `api/`: Backend services (FastAPI)
- `frontend_pro/`: Frontend application (Vite + React)
- `core/`: Core logic and data pipelines
- `output/`: Generated assets (JSON, Excel, Images)

### 🔧 Configuration
Ensure a `.env` file exists in the root directory:
- `ALGATOP_USER` / `ALGATOP_PASS`: Credentials
- `SUPABASE_URL` / `SUPABASE_KEY`: Database settings

---

<h2 id="中文">🇨🇳 中文</h2>

### 项目简介
**ProSourcing** 是一个完整的 AI 选品分析系统。它集成了 **RPA 自动采集**、**潜力评分算法** 和 **可视化报表**，旨在帮助用户快速从海量市场数据中挖掘出具有潜力的爆款产品。

### 🚀 快速启动
你可以通过以下命令一键启动后端（FastAPI）和前端（Vite）：
```powershell
python run_dev.py
```

### 🛠️ 核心工作流
1.  **RPA 采集**：运行脚本抓取 Algatop 类目数据。
    ```powershell
    python core/algatop_rpa_scraper.py [类目代码]
    ```
2.  **数据分析与入库**：同步本地数据至 Supabase 并生成 Excel 分析报告。
    ```powershell
    python core/rpa_final_pipeline.py
    ```

### 🗄️ 数据库环境分流 (开发/生产)
系统支持通过 `ENV_MOD` 环境变量实现数据库的“一键切流”：
1.  **开发环境 (Local)**: 默认连接 **Supabase 云端**，配置读取自 `.env`。
2.  **生产环境 (Docker)**: 设置 `ENV_MOD=production`，连接容器内 **PostgreSQL**。

> [!IMPORTANT]
> **写入数据的归宿**：在 Docker 中运行时，数据进入本地 PG；在本地直接运行脚本时，数据同步到 Supabase。

---
<div align="center">
  <p>Made with ❤️ by the ProSourcing Team</p>
</div>
