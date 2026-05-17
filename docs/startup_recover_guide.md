# ProSourcing 重启后操作说明

适用路径：`D:\ProSourcing`

## 一、电脑重启后怎么操作

1. 先在桌面找到并打开 `Docker Desktop`
2. 等待 Docker Desktop 完全启动
3. 打开项目目录：`D:\ProSourcing`
4. 进入 `scripts` 文件夹
5. 双击运行：`startup_recover.bat`
6. 等待终端窗口自动执行，不要中途关闭

## 二、先确认 Docker Desktop 已启动

打开 Docker Desktop 后，建议先等待 10 到 30 秒。

如果 Docker Desktop 还没有完全启动，脚本里可能会看到 Docker 相关报错。

简单判断方法：

1. 桌面已经打开了 Docker Desktop
2. Docker Desktop 不再显示启动中的加载状态
3. 再去双击 `startup_recover.bat`

## 三、正常情况下会看到什么

脚本会按步骤执行，正常会依次看到以下内容：

1. `STEP 1 检查 Docker 并启动容器`
2. `Docker daemon 已就绪`
3. `prosourcing_db: status=running`
4. `prosourcing_backend: status=running`
5. `prosourcing_frontend: status=running`
6. `STEP 2 检查浏览器并恢复登录态`
7. `Chrome 已启动` 或 `复用现有浏览器`
8. `Algatop 登录态仍然有效` 或 `Algatop 自动登录成功`
9. `STEP 4 访问地址`

最后会打印访问地址，例如：

```text
前端本机地址: http://localhost
前端局域网地址: http://192.168.x.x
后端本机地址: http://localhost:8000
后端局域网地址: http://192.168.x.x:8000
```

## 四、什么情况表示启动成功

满足下面 3 条，就表示启动成功：

1. 终端里看到：
   `prosourcing_db: status=running`
   `prosourcing_backend: status=running`
   `prosourcing_frontend: status=running`
2. 终端里看到：
   `Algatop 登录态仍然有效`
   或
   `Algatop 自动登录成功`
3. 最后打印出了访问地址

## 五、成功后怎么检查系统是否可用

1. 在本机浏览器打开：
   `http://localhost`
2. 如果需要给同一局域网内其他电脑访问，打开终端最后打印的：
   `前端局域网地址`
3. 如果前端页面能打开，说明系统基本启动成功

## 六、如果没有成功，怎么处理

### 情况 1：Docker 相关报错

如果看到以下内容，说明容器没有正常启动：

- `Docker 步骤失败`
- `部分 Docker 容器没有成功启动`
- 某个容器不是 `status=running`

处理方法：

1. 先确认桌面上的 `Docker Desktop` 已经打开
2. 等待 Docker Desktop 完全启动
3. 再次双击运行 `startup_recover.bat`
4. 如果还是失败，联系技术人员，并把终端窗口拍照或截图
5. 同时提供日志文件：
   `D:\ProSourcing\logs\startup_recover.log`

### 情况 2：忘记打开 Docker Desktop

如果电脑刚重启，最常见的问题就是还没有先打开 Docker Desktop。

处理方法：

1. 回到桌面
2. 双击打开 `Docker Desktop`
3. 等待 Docker Desktop 完全启动
4. 再回到 `D:\ProSourcing\scripts`
5. 双击运行 `startup_recover.bat`

### 情况 3：浏览器没有自动打开

处理方法：

1. 等待 10 到 20 秒
2. 再次双击运行 `startup_recover.bat`
3. 如果还是没有打开，联系技术人员，并提供日志文件

### 情况 4：浏览器打开了，但没有登录成功

如果看到以下内容，说明登录没有恢复成功：

- `检测到登录态失效`
- `Automatic login did not leave the login page`
- 浏览器停留在登录页

处理方法：

1. 在浏览器中手动登录 Algatop 账号
2. 登录成功后，不要关闭浏览器
3. 回到项目目录，再次双击 `startup_recover.bat`

### 情况 5：打开网址失败

如果最后打印了网址，但网页打不开：

1. 先确认终端里 3 个容器都是 `status=running`
2. 如果容器不是全部 `running`，按“情况 1”处理
3. 如果容器都是 `running`，但网页打不开，联系技术人员并提供：
   - 终端截图
   - `D:\ProSourcing\logs\startup_recover.log`

## 七、给用户的简单判断方法

用户只需要记住：

### 成功标准

- 已经先打开 Docker Desktop
- 看见 3 个容器都是 `running`
- 看见浏览器登录成功
- 看见最后打印了访问地址
- 打开 `http://localhost` 能看到系统页面

### 失败标准

- Docker Desktop 没打开
- 终端出现 `[FAIL]`
- 某个容器不是 `running`
- 浏览器一直没有打开
- 浏览器打开后还停留在登录页
- 最后没有打印访问地址

## 八、需要提供给技术人员的信息

如果失败，请把下面两样发给技术人员：

1. 终端窗口完整截图
2. 日志文件：
   `D:\ProSourcing\logs\startup_recover.log`
