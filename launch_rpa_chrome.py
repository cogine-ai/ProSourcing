import os
import subprocess

def launch_chrome_for_rpa():
    # 默认 Chrome 路径（Windows）
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    
    # 调试端口和独立的用户数据目录（防止干扰你平时的浏览器）
    port = 9222
    user_data_dir = r"C:\AlgatopRPA_ChromeData"
    
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
        
    cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    
    print(f"正在启动 Chrome 调试模式...")
    print(f"指令: {' '.join(cmd)}")
    print(f"\n请在打开的浏览器中登录 Algatop 账号，然后运行采集脚本。")
    
    subprocess.Popen(cmd)

if __name__ == "__main__":
    launch_chrome_for_rpa()
