import os
import sys
import requests
from bs4 import BeautifulSoup

# 保存原始 HTML 到本地查看
url = "https://kaspi.kz/shop/c/categories/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
}

try:
    print(f"🚀 发送请求到 {url}...")
    response = requests.get(url, headers=headers, timeout=15)
    print(f"📡 响应状态码: {response.status_code}")
    
    with open("kaspi_debug.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("💾 原始 HTML 已保存到 kaspi_debug.html")

    soup = BeautifulSoup(response.text, 'html.parser')
    # 打印前 500 个字符
    print("\n🔍 页面前 500 个字符预览:")
    print(response.text[:500])
    
    # 查找是否包含 "Одежда" 这个词
    if "Одежда" in response.text:
        print("\n✅ 页面源码中包含 'Одежда'")
    else:
        print("\n❌ 页面源码中不包含 'Одежда'，可能被拦截或动态加载了")

except Exception as e:
    print(f"❌ 发生异常: {e}")
