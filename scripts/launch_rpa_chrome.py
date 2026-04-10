import os
import subprocess
import sys

def launch_chrome_for_rpa():
    # 1. 自动寻找 Chrome 路径
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get('LocalAppData', 'C:\\Users\\Default\\AppData\\Local'), r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), r"Google\Chrome\Application\chrome.exe"),
    ]
    
    chrome_path = None
    for path in possible_paths:
        if os.path.exists(path):
            chrome_path = path
            break
    
    if not chrome_path:
        print("❌ 没找着 Chrome！哥，你确认这台电脑装 Chrome 了吗？")
        return

    # 2. 调试端口
    port = 9222
    
    # 3. 把用户数据存在项目当前目录的 tmp/chrome_data 下，这样方便“拎包就走”
    current_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(current_dir, "tmp", "chrome_rpa_profile")
    
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir, exist_ok=True)
        
    cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1280,720"
    ]
    
    print(f"🚀 正在启动 Chrome RPA 模式...")
    print(f"📍 浏览器路径: {chrome_path}")
    print(f"📁 数据存储位: {user_data_dir}")
    
    subprocess.Popen(cmd)
    print(f"\n✅ 启动成功！请在打开的浏览器中登录 Algatop 账号。")

if __name__ == "__main__":
    launch_chrome_for_rpa()

