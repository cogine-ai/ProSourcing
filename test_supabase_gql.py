import requests
import json

url = "https://furwnoxzsddkytimxtma.supabase.co/graphql/v1"
headers = {
    "apikey": "sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H",
    "Authorization": "Bearer sb_publishable_YcF-ou8VD7TvqzbhOTF0ew_MPI0Wv3H",
    "Content-Type": "application/json"
}

query = """
{
  __schema {
    types {
      name
      fields {
        name
        type {
          name
          kind
        }
      }
    }
  }
}
"""

try:
    res = requests.post(url, headers=headers, json={"query": query})
    if res.status_code == 200:
        schema = res.json().get("data", {}).get("__schema", {})
        types = schema.get("types", [])
        
        # Filter built-in types
        user_types = [t for t in types if t["name"] and not t["name"].startswith("__") and t["name"] not in ["Query", "Mutation", "Subscription", "String", "Boolean", "Int", "Float", "ID", "UUID", "JSON", "BigInt", "Date", "Time", "Datetime", "Cursor", "PageInfo", "OrderByDirection", "FilterString", "FilterInt", "FilterUUID", "FilterDatetime", "FilterFloat", "FilterBoolean", "FilterBigInt", "Node", "CollectionInfo", "Cursor", "PageInfo"]]
        
        print("Detected GraphQL Types (Likely Tables):")
        for t in user_types:
            print(f"- {t['name']}")
            fields = t.get("fields")
            if fields:
                for f in fields:
                    print(f"  - {f['name']}")
    else:
        print(f"Error {res.status_code}: {res.text}")
except Exception as e:
    print(f"Exception: {e}")
