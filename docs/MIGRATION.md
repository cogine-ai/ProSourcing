# ProSourcing 迁移指南 (Docker 快速版)

哥，按下面这个“三步走”策略，保你在新电脑上 1 分钟起飞。

### 第一步：准备迁移包
在旧电脑的项目根目录，把这些核心文件打包：
1. **配置文件**：`.env` (必须带，里面有你的 API Key 和数据库密码)
2. **启动配置**：`docker-compose.yml`, `scripts/init.sql`
3. **环境镜像** (如果你不想在新电脑上 build)：
   - `prosourcing_backend_ultimate.tar`
   - `prosourcing_frontend.tar`
   - `postgres_15_alpine.tar`
4. **持久化数据** (可选)：
   - `tmp/chrome_rpa_profile/` (带上这个，新电脑免扫码登录 Kaspi)
   - `logs/`, `output/`

### 第二步：新电脑部署
把包解压后，在文件夹里打开终端，执行以下命令导入镜像：
```powershell
docker load -i postgres_15_alpine.tar
docker load -i prosourcing_backend_ultimate.tar
docker load -i prosourcing_frontend.tar
```

### 第三步：一键启动
如果你已经拷贝了 `.tar` 镜像，直接跑：
```powershell
docker-compose up -d
```
如果你没拷贝镜像包，但拷贝了源码，跑（这会自动重新构建）：
```powershell
docker-compose up -d --build
```

---

### ⚠️ 注意事项
1. **Chrome 路径**：请确保新电脑安装了 Google Chrome。
2. **端口占用**：如果新电脑 80 端口被占了，请修改 `.env` 里的 `FRONTEND_PORT=8080` (或其他你喜欢的数字)。
3. **数据导入**：如果你要把旧电脑的数据库记录也带走，建议参考 `README.md` 里的数据库备份部分。

哥，祝你迁移顺利！有事儿叫我。
