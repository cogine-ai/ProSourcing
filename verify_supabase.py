import requests
import json

url = "https://furwnoxzsddkytimxtma.supabase.co/rest/v1/products_raw_data"
headers = {
    "apikey": "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H",
    "Authorization": "Bearer sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H"
}

res = requests.get(f"{url}?select=sku,product_name,listing_date,category_tree,category_total_sales,category_total_products,top3_sales_sum,sales_3m&limit=20", headers=headers)
print(f"Status: {res.status_code}")
if res.status_code == 200:
    data = res.json()
    print(f"Records in Supabase: {len(data)}")
    for r in data:
        print(r)
else:
    print(res.text)
