import requests
import json
import os
import sys

# 设置基础 URL 和 Headers
API_URL = "https://kaspi.kz/yml/main-navigation/n/n/desktop-menu?depth=10&city=750000000&code&rootType=desktop"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://kaspi.kz/shop/c/categories/"
}

def fetch_full_tree():
    print(f"🚀 正在尝试获取 Kaspi 全量类目树 (Depth: 10)...")
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        # 结果存为 JSON 文件供分析
        with open("kaspi_full_tree_raw.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print("✅ 原始数据已保存到 kaspi_full_tree_raw.json")
        
        # 统计节点数量
        total_nodes = 0
        def count_nodes(node):
            nonlocal total_nodes
            total_nodes += 1
            if 'subNodes' in node and node['subNodes']:
                for sub in node['subNodes']:
                    count_nodes(sub)
        
        if 'subNodes' in data:
            for root_node in data['subNodes']:
                count_nodes(root_node)
        
        print(f"📈 扫描完成，共发现 {total_nodes} 个层级节点。")
        
    except Exception as e:
        print(f"❌ 获取失败: {e}")

if __name__ == "__main__":
    fetch_full_tree()
