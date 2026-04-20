import argparse
import asyncio
import ipaddress
import json
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv as _load_dotenv
except ImportError:
    _load_dotenv = None
try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except ImportError:
    PlaywrightTimeoutError = Exception
    async_playwright = None


ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
DEFAULT_PROFILE_DIR = ROOT_DIR / "chrome_user_data"
DEFAULT_AUTH_PATH = ROOT_DIR / "auth.json"
DEFAULT_DEBUG_PORT = 9222
DEFAULT_LOGIN_URL = "https://app.algatop.kz/auth/login/mail"
DEFAULT_CHECK_URL = "https://app.algatop.kz/niche/category/04456"
EXPECTED_CONTAINERS = [
    "prosourcing_db",
    "prosourcing_backend",
    "prosourcing_frontend",
]
DEFAULT_FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "80") or "80")
DEFAULT_BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000") or "8000")


def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "startup_recover.log"

    logger = logging.getLogger("startup_recover")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    try:
        if sys.stdout and hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
    except Exception:
        pass

    return logger


LOGGER = setup_logging()


def step_banner(index: int, title: str) -> None:
    message = f"[STEP {index}] {title}"
    print("\n" + "=" * len(message))
    print(message)
    print("=" * len(message))
    LOGGER.info(message)


def step_ok(message: str) -> None:
    print(f"[OK] {message}")
    LOGGER.info(message)


def step_warn(message: str) -> None:
    print(f"[WARN] {message}")
    LOGGER.warning(message)


def step_fail(message: str) -> None:
    print(f"[FAIL] {message}")
    LOGGER.error(message)


def get_local_ip() -> str:
    candidates: list[str] = []

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip not in candidates:
                candidates.append(ip)
    except Exception:
        pass

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        if ip not in candidates:
            candidates.insert(0, ip)
    except Exception:
        pass
    finally:
        try:
            sock.close()
        except Exception:
            pass

    preferred_prefixes = ("192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")
    for ip in candidates:
        if ip.startswith(preferred_prefixes):
            return ip

    for ip in candidates:
        try:
            parsed = ipaddress.ip_address(ip)
            if not parsed.is_loopback and not parsed.is_link_local and not parsed.is_multicast:
                if not ip.startswith("198.18.") and not ip.startswith("198.19."):
                    return ip
        except ValueError:
            continue

    return "127.0.0.1"


def format_url(host: str, port: int, path: str = "") -> str:
    if port == 80:
        return f"http://{host}{path}"
    if port == 443:
        return f"https://{host}{path}"
    return f"http://{host}:{port}{path}"


def load_env() -> None:
    env_path = ROOT_DIR / ".env"

    if _load_dotenv is not None:
        _load_dotenv(env_path)
        return

    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


def run_command(command: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    display = " ".join(command)
    print(f"[CMD] {display}")
    LOGGER.info("Running command: %s", display)
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if result.stdout and result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr and result.stderr.strip():
        print(result.stderr.strip())
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            command,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def find_chrome_path() -> str | None:
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LocalAppData", r"C:\Users\Default\AppData\Local"), r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), r"Google\Chrome\Application\chrome.exe"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def try_start_docker_desktop() -> bool:
    docker_desktop = os.path.join(
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        "Docker",
        "Docker",
        "Docker Desktop.exe",
    )
    if os.path.exists(docker_desktop):
        step_warn("Docker daemon 未就绪，尝试启动 Docker Desktop。")
        subprocess.Popen([docker_desktop], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    return False


def try_start_docker_service() -> bool:
    try:
        result = run_command(
            ["powershell", "-NoProfile", "-Command", "Get-Service -Name com.docker.service -ErrorAction Stop | Select-Object -ExpandProperty Status"],
            check=False,
        )
        if result.returncode != 0:
            return False
        status = (result.stdout or "").strip()
        if status.lower() != "running":
            step_warn("尝试启动 Windows 服务 com.docker.service。")
            run_command(["powershell", "-NoProfile", "-Command", "Start-Service -Name com.docker.service"], check=False)
        return True
    except Exception:
        return False


def ensure_docker_ready(timeout_seconds: int = 180) -> None:
    start_time = time.time()
    recovery_triggered = False

    while time.time() - start_time < timeout_seconds:
        result = run_command(["docker", "info"], check=False)
        if result.returncode == 0:
            step_ok("Docker daemon 已就绪。")
            return

        if not recovery_triggered:
            recovery_triggered = True
            started = try_start_docker_service()
            started = try_start_docker_desktop() or started
            if started:
                step_warn("已触发 Docker 恢复动作，等待 daemon 可用。")
            else:
                step_warn("Docker daemon 仍不可用，继续等待。")

        time.sleep(5)

    raise RuntimeError("Docker daemon was not ready within timeout.")


def start_existing_containers() -> bool:
    started_any = False

    for name in EXPECTED_CONTAINERS:
        inspect = run_command(["docker", "inspect", name], check=False)
        if inspect.returncode != 0:
            step_warn(f"未找到现有容器: {name}")
            continue

        start_result = run_command(["docker", "start", name], check=False)
        if start_result.returncode == 0:
            started_any = True

    return started_any


def ensure_compose_up() -> None:
    try:
        run_command(["docker", "compose", "up", "-d"], cwd=ROOT_DIR)
        step_ok("Docker 容器启动完成。")
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        stdout = exc.output or ""
        combined = f"{stdout}\n{stderr}".strip()

        if "container name" in combined.lower() and "already in use" in combined.lower():
            step_warn("检测到容器名冲突，尝试直接启动现有容器。")
            if start_existing_containers():
                step_ok("已复用并启动现有 Docker 容器。")
                return

        raise


def get_container_status(name: str) -> tuple[str, str]:
    result = run_command(
        [
            "docker",
            "inspect",
            name,
            "--format",
            "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
        ],
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return ("missing", "none")

    raw = result.stdout.strip().split("|", 1)
    status = raw[0].strip() if raw else "unknown"
    health = raw[1].strip() if len(raw) > 1 else "none"
    return (status, health)


def verify_docker_containers() -> bool:
    print("[INFO] 检查 Docker 容器实际状态...")
    all_running = True

    for name in EXPECTED_CONTAINERS:
        status, health = get_container_status(name)
        if status != "running":
            all_running = False
            step_warn(f"{name}: status={status}, health={health}")
        else:
            step_ok(f"{name}: status={status}, health={health}")

    return all_running


def print_access_urls() -> None:
    local_ip = get_local_ip()
    frontend_port = int(os.getenv("FRONTEND_PORT", str(DEFAULT_FRONTEND_PORT)) or DEFAULT_FRONTEND_PORT)
    backend_port = int(os.getenv("BACKEND_PORT", str(DEFAULT_BACKEND_PORT)) or DEFAULT_BACKEND_PORT)

    step_banner(4, "访问地址")
    step_ok(f"前端本机地址: {format_url('localhost', frontend_port)}")
    step_ok(f"前端局域网地址: {format_url(local_ip, frontend_port)}")
    step_ok(f"后端本机地址: {format_url('localhost', backend_port)}")
    step_ok(f"后端局域网地址: {format_url(local_ip, backend_port)}")


def launch_chrome_if_needed(port: int, profile_dir: Path) -> None:
    if is_port_open(port):
        step_ok(f"Chrome 调试端口 {port} 已存在，复用现有浏览器。")
        return

    chrome_path = find_chrome_path()
    if not chrome_path:
        raise RuntimeError("Chrome executable was not found.")

    profile_dir.mkdir(parents=True, exist_ok=True)
    command = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1440,900",
        "--new-window",
        DEFAULT_LOGIN_URL,
    ]
    print(f"[INFO] Chrome 用户目录: {profile_dir}")
    LOGGER.info("Launching Chrome with persistent profile: %s", profile_dir)
    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for _ in range(30):
        if is_port_open(port):
            step_ok(f"Chrome 已启动，调试端口 {port} 就绪。")
            return
        time.sleep(1)

    raise RuntimeError("Chrome did not expose the debug port in time.")


async def ensure_algatop_login(port: int, username: str | None, password: str | None, auth_path: Path) -> None:
    if async_playwright is None:
        step_warn("Playwright not installed, skipping automatic Algatop login recovery.")
        return

    if not username or not password:
        step_warn("ALGATOP_USER or ALGATOP_PASS missing, skipping login.")
        return

    async with async_playwright() as p:
        print(f"[INFO] 正在连接本地 Chrome: 127.0.0.1:{port}")
        LOGGER.info("Connecting to Chrome over CDP on port %s.", port)
        browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()

        try:
            await page.bring_to_front()
            print("[INFO] 检查 Algatop 登录状态...")
            LOGGER.info("Checking Algatop session status.")
            await page.goto(DEFAULT_CHECK_URL, wait_until="domcontentloaded", timeout=60000)
            await page.bring_to_front()
            await asyncio.sleep(3)

            if "login" in page.url.lower():
                step_warn("检测到登录态失效，开始自动登录。")
                await page.goto(DEFAULT_LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
                await page.bring_to_front()
                await page.wait_for_selector('input[type="email"], input[name="email"]', timeout=30000)
                await page.fill('input[type="email"], input[name="email"]', username)
                await page.fill('input[type="password"]', password)
                await page.click('button[type="submit"]')

                try:
                    await page.wait_for_url("**/niche/**", timeout=45000)
                except PlaywrightTimeoutError:
                    await asyncio.sleep(8)

                if "login" in page.url.lower():
                    raise RuntimeError("Automatic login did not leave the login page. Manual verification may be required.")

                step_ok("Algatop 自动登录成功。")
            else:
                step_ok("Algatop 登录态仍然有效。")

            auth_state = await context.storage_state()
            auth_path.write_text(json.dumps(auth_state, ensure_ascii=False, indent=2), encoding="utf-8")
            step_ok(f"登录状态已保存到 {auth_path}")
        finally:
            await page.close()
            await browser.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recover ProSourcing services after server reboot.")
    parser.add_argument("--skip-docker", action="store_true", help="Skip docker readiness check and compose startup.")
    parser.add_argument("--skip-browser", action="store_true", help="Skip Chrome launch and Algatop login recovery.")
    parser.add_argument("--port", type=int, default=DEFAULT_DEBUG_PORT, help="Chrome remote debugging port.")
    parser.add_argument("--profile-dir", default=str(DEFAULT_PROFILE_DIR), help="Chrome user data directory.")
    parser.add_argument("--auth-path", default=str(DEFAULT_AUTH_PATH), help="Path to write storage_state JSON.")
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    load_env()
    docker_failed = False

    print("ProSourcing 启动恢复脚本")
    print(f"项目目录: {ROOT_DIR}")
    print(f"日志文件: {LOG_DIR / 'startup_recover.log'}")
    LOGGER.info("Startup recovery begins.")

    if not args.skip_docker:
        step_banner(1, "检查 Docker 并启动容器")
        docker_failed = False
        try:
            ensure_docker_ready()
            ensure_compose_up()
            if verify_docker_containers():
                step_ok("Docker 相关容器均已启动。")
            else:
                docker_failed = True
                step_warn("部分 Docker 容器没有成功启动。")
        except Exception as exc:
            docker_failed = True
            step_warn(f"Docker 步骤失败，但继续执行浏览器恢复: {exc}")
    else:
        step_warn("已跳过 Docker 恢复。")

    if not args.skip_browser:
        step_banner(2, "检查浏览器并恢复登录态")
        profile_dir = Path(args.profile_dir)
        auth_path = Path(args.auth_path)
        launch_chrome_if_needed(args.port, profile_dir)
        await ensure_algatop_login(
            port=args.port,
            username=os.getenv("ALGATOP_USER"),
            password=os.getenv("ALGATOP_PASS"),
            auth_path=auth_path,
        )
    else:
        step_warn("已跳过浏览器恢复。")

    step_banner(3, "收尾")
    if not args.skip_docker and docker_failed:
        step_warn("浏览器已继续处理，但 Docker 步骤存在失败，请检查上面的报错。")
    step_ok("全部步骤执行完成。")
    print_access_urls()
    LOGGER.info("Startup recovery completed successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(async_main()))
    except Exception as exc:
        step_fail(f"启动恢复失败: {exc}")
        LOGGER.exception("Startup recovery failed: %s", exc)
        raise SystemExit(1)
