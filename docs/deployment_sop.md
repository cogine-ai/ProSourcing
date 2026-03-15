# 📦 ProSourcing AI：零基础“傻瓜式”部署手册（保姆级）

哥，为了让咱们的新同事甚至非技术人员都能一眼看懂，我把流程精简到了极点。不管是现场断网还是没装环境，只要跟着这四步走，保证 10 分钟内跑起来！

---

## 🛑 第一步：出发前，在自己电脑“打包”
> 目标：把所有复杂的代码和依赖变成 3 个大文件，装进 U 盘。

1.  **打开项目文件夹**：找到 `scripts` 文件夹。
2.  **点击脚本**：右键点击 [pack_images.ps1](file:///d:/item/ProSourcing/scripts/pack_images.ps1)，选择“使用 PowerShell 运行”。
3.  **等待结束**：等黑色窗口自动关闭后，你会发现文件夹里多了 3 个 `.tar` 结尾的大文件。
4.  **拷贝资料**：把下面这些文件**全部拷贝**到 U 盘根目录：
    - [ ] `scripts/` 文件夹（全拷）
    - [ ] [docker-compose.yml](file:///d:/item/ProSourcing/docker-compose.yml) (重要)
    - [ ] [.env](file:///d:/item/ProSourcing/.env) (核心配置)
    - [ ] [launch_rpa_chrome.py](file:///d:/item/ProSourcing/launch_rpa_chrome.py) (拉浏览器用)
    - [ ] `prosourcing_backend.tar` (刚生成的)
    - [ ] `prosourcing_frontend.tar` (刚生成的)
    - [ ] `postgres_15_alpine.tar` (刚生成的)

---

## 🛠️ 第二步：到现场，安装基础工具
> 目标：给客户电脑装上“地基”。

1.  **安装 Docker**：在客户电脑通过 U 盘里的安装包（或下载）安装 `Docker Desktop`。
    - *检查点*：安装完重启电脑，看到右下角有个小鲸鱼图标在游动就说明好了。
2.  **安装 Python**：安装最新版 Python。
    - *必看*：安装时一定要勾选 `Add Python to PATH`。

---

## 🚀 第三步：开始部署（核心动作）
> 目标：把 U 盘里的东西“灌”进电脑，并配置好账号。

1.  **准备文件夹**：在客户电脑 D 盘建个文件夹（如 `D:\ProSourcing`），把 U 盘里的东西**全部粘贴**进去。
2.  **导入镜像**：进入 `scripts` 文件夹，右键点击 [load_images.ps1](file:///d:/item/ProSourcing/scripts/load_images.ps1)，选择“使用 PowerShell 运行”。
3.  **修改配置**：用记事本打开 [.env](file:///d:/item/ProSourcing/.env) 文件。
    - [ ] 改一下 `ALGATOP_USER` (账号) 和 `ALGATOP_PASS` (密码)。
    - [ ] 确保第一行写着 `ENV_MOD=production`。

---

## 🎬 第四步：启动与验证
> 目标：顺利跑通全流程。

1.  **拉起浏览器**：在文件夹里双击运行 [launch_rpa_chrome.py](file:///d:/item/ProSourcing/launch_rpa_chrome.py)。
    - *动作*：电脑会弹出一个 Chrome 浏览器。请在这个浏览器里**手动登录**好账号。
2.  **一键启动服务**：
    - 在文件夹空白处，按住 `Shift` 键点击右键，选择“在此处打开 PowerShell 窗口”。
    - 输入命令并敲回车：`docker-compose up -d`
3.  **看结果**：
    - **打开浏览器**：输入 `localhost` 就能看到系统界面。
    - **核对数据**：系统能显示东西，且采集不报错，大功告成！

---

### 🔥 常见问题（保命指南）
- **如果没动静**：检查右下角的小鲸鱼是不是绿色的。
- **如果网页打不开**：检查 [.env](file:///d:/item/ProSourcing/.env) 文件里的配置有没有写错。
- **如果要换账号**：关掉弹出的 Chrome，重新运行 [launch_rpa_chrome.py](file:///d:/item/ProSourcing/launch_rpa_chrome.py) 登录新账号即可。

哥，这套 SOP 任何人拿上手都能操作。你是带队大哥，有这手册在手，现场派谁去都不怕！
