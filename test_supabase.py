import requests
import json

url = "https://furwnoxzsddkytimxtma.supabase.co/rest/v1/"
headers = {
    "apikey": "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H",
    "Authorization": "Bearer sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
}

try:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("Successfully connected. Available tables/endpoints:")
        paths = data.get("paths", {}).keys()
        tables = [p.strip('/') for p in paths if p != '/']
        print(tables)
        
        # 尝试读取第一个表的结构和数据
        if tables:
            first_table = tables[0]
            table_url = f"{url}{first_table}?select=*&limit=1"
            res = requests.get(table_url, headers=headers)
            print(f"\nData from {first_table}:")
            print(json.dumps(res.json(), indent=2, ensure_ascii=False))
    else:
        print(f"Failed to connect: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
