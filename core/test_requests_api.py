import requests
import json
import datetime
import os

def test_api_requests():
    print("\n--- Testing Algatop API with Native Requests ---")
    
    # 从文件中读取刚才 dump 的 cookie
    cookie_path = "d:/item/ProSourcing/output/cookies_raw.txt"
    if not os.path.exists(cookie_path):
        print("Cookie file not found")
        return
        
    with open(cookie_path, "r") as f:
        cookie_str = f.read().strip()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://app.algatop.kz/niche",
        "top-l": "2s3dfnfRgn43PkgmPolqre#",
        "Accept": "application/json, text/plain, */*",
        "Cookie": cookie_str
    }

    end_date = datetime.date.today().strftime("%Y%m%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y%m%d")
    
    # 测试 ID: 00126 (Гаджеты)
    test_id = "00126"
    url = f"https://app.algatop.kz/api/v1/niche/categoryListStatistic?startDate={start_date}&endDate={end_date}&categoryId={test_id}"
    
    print(f"Requesting URL: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nResponse Data:")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
        else:
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_api_requests()
