import requests
import json

def test_api():
    url = "http://127.0.0.1:8000/api/kaspi/tree"
    print(f"Testing API: {url} ...")
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.data if hasattr(res, 'data') else res.json()
            print(f"Successfully fetched tree. Top level roots: {len(data)}")
            # 统计总节点数
            def count_nodes(nodes):
                count = len(nodes)
                for n in nodes:
                    if n.get('children'):
                        count += count_nodes(n['children'])
                return count
            
            total = count_nodes(data)
            print(f"Total nodes in tree: {total}")
            
            # 检查第一个 root 
            if data:
                print("Sample root node:")
                print(json.dumps(data[0], indent=2, ensure_ascii=False)[:500])
        else:
            print(f"API Error: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Connection failed (is the server running?): {e}")

if __name__ == "__main__":
    test_api()
