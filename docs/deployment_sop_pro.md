# 🏠 ProSourcing AI 采集系统：保姆级安装与操作指南 (V3.0)

哥，这套手册我按“保洁阿姨级”难度重写了。哪怕没摸过代码，只要会点鼠标、会打字，按着一步步来绝对能成！

---

## 🏗️ 第一阶段：准备工作 (下载与拷文件)
> **目标**：把所有的“零件”都准备齐全，带进 U 盘。

### 1. 必下的软件包 (去官网下最新的)
- **Python**: [点击下载 Python 3.10](https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe)
- **Docker**: [点击下载 Docker Desktop](https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe)
- **Chrome 浏览器**: 如果目标电脑没装，必须装一个。

### 2. U 盘里必须有的文件单
请把以下文件全部拷进 U 盘的一个文件夹里：
- ✅ `python-3.10.11-amd64.exe` (刚下的安装包)
- ✅ `Docker Desktop Installer.exe` (刚下的安装包)
- ✅ `prosourcing_backend_ultimate.tar` (系统核心包，最重要！)
- ✅ `.env` (配置文件)
- ✅ `docker-compose.yml` (系统图纸)
- ✅ `launch_rpa_chrome.py` (浏览器的“遥控器”)
- ✅ `AI产品开发.xlsx` (报表模板)

---

## 🚀 第二阶段：现场安装 (傻瓜式三步走)

### 第一步：装软件 (一路点“下一步”)
1. **安装 Python**：
   - 双击 `python-3.10.11`。
   - **⚠️ 特别注意**：底部有一个 **`Add Python to PATH`**，必须打勾！没打勾就得重装。
   - 点 `Install Now`。
2. **安装 Docker**：
   - 双击 `Docker Desktop Installer`。
   - 一路点 OK，装完后会提示重启电脑。**必须重启！**
   - 重启后，双击桌面小鲸鱼图标，等它变绿（Running）。

### 第二步：抄文件 (搬运工时间)
1. 在客户电脑 **D 盘** 建立一个文件夹，起名叫 `ProSourcing`。
2. 把 U 盘里剩下的所有文件全部复制进去。
3. **最终 D:\ProSourcing 文件夹里应该长这样：**
   - `output/` (空文件夹，抓完的东西在这)
   - `.env`
   - `docker-compose.yml`
   - `prosourcing_backend_ultimate.tar`
   - `launch_rpa_chrome.py`
   - `AI产品开发.xlsx`

### 第三步：点火启动 (复制粘贴命令)
1. 在 `D:\ProSourcing` 文件夹的空白处，按住键盘 **Shift 键**，同时点**鼠标右键**。
2. 选择“在此处打开 PowerShell 窗口”或“在此处打开终端”。
3. **粘贴第一条指令 (加载系统)**:
   ```powershell
   docker load -i prosourcing_backend_ultimate.tar
   ```
   (等它跑完，显示 Loaded image...)
4. **粘贴第二条指令 (启动系统)**:
   ```powershell
   docker-compose up -d
   ```
   (看到三个绿色 `Started`，系统就原地复活了！)

---

## 🎮 第三阶段：日常操作 (怎么用它干活)

### 1. 开启“上帝浏览器”
- **每天开始干活前**，先双击运行那个 `launch_rpa_chrome.py`。
- 会弹出一个 Chrome 窗口，请在里面登录你的 **Algatop 账号**。
- **⚠️ 注意**：这个窗口千万别关，缩小到后台就行。

### 2. 去网页点点点
- 打开浏览器访问地址：`http://localhost`。
- 类目树出来后，点“开始采集”。

---

## ⚠️ 避坑与注意事项 (保命指南)

### 1. 换号了怎么办？
- 当账号没额度了：
  - 右键记事本打开 `.env` 文件。
  - 把 `ALGATOP_USER` 和 `ALGATOP_PASS` 换成新的。
  - **关键点**：关掉所有 Chrome 窗口，重新双击 `launch_rpa_chrome.py` 登录新号。

### 2. 进度条不动了？
- 刷新网页看一眼。
- 确认 `launch_rpa_chrome.py` 弹出来的那个黑框还在不在跑。

### 3. 数据怎么拿？
- 所有的 Excel 报表和原始数据都在 `D:\ProSourcing\output` 文件夹里。

---

## 🚨 常见报错自救手册
- **报错 500/连接失败**：多半是开了翻墙软件。**请关闭 Clash/V2Ray 等代理程序**，或者把代理退出再试。
- **找不到文件**：确认文件夹路径是 `D:\ProSourcing`，且 `AI产品开发.xlsx` 就在这个文件夹里。
- **端口冲突**：如果启动失败，请检查 8000 端口是不是被别的软件占了。

---
哥，这就是最全的说明了。只要这套文件全，谁来都能在 5 分钟内把整套系统跑起来！🚀
