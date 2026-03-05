import requests
import json

try:
    r = requests.get('http://127.0.0.1:8000/api/categories/top_stats')
    data = r.json()
    print(f"Total tops: {len(data)}")
    for d in data:
        name = d.get('category_name')
        leaves = d.get('leaves', [])
        print(f"Category: {name} | Leaves: {len(leaves)}")
except Exception as e:
    print(f"Error: {e}")
