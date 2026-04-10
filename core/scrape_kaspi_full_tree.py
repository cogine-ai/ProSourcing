import json
import os

import requests

API_URL = "https://kaspi.kz/yml/main-navigation/n/n/desktop-menu?depth=10&city=750000000&code&rootType=desktop"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://kaspi.kz/shop/c/categories/",
}
OUTPUT_PATH = os.path.join("tmp", "root-artifacts", "kaspi_full_tree_raw.json")


def fetch_full_tree():
    print("Starting Kaspi full tree fetch (depth: 10)...")
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()

        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        print(f"Saved raw tree to {OUTPUT_PATH}")

        total_nodes = 0

        def count_nodes(node):
            nonlocal total_nodes
            total_nodes += 1
            for sub_node in node.get("subNodes", []) or []:
                count_nodes(sub_node)

        for root_node in data.get("subNodes", []) or []:
            count_nodes(root_node)

        print(f"Scan complete, found {total_nodes} nodes.")
    except Exception as error:
        print(f"Fetch failed: {error}")


if __name__ == "__main__":
    fetch_full_tree()
