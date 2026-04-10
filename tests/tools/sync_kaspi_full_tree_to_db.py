import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.final_pipeline import supabase

JSON_PATH = os.path.join("tmp", "root-artifacts", "kaspi_full_tree_raw.json")


def sync_tree_to_db():
    if not os.path.exists(JSON_PATH):
        print(f"Missing raw tree file: {JSON_PATH}")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as file:
        raw_data = json.load(file)

    all_categories = []

    def process_node(node, parent_id=None):
        cat_id = node.get("code")
        if not cat_id:
            return

        qty = 0
        if node.get("data") and "popularity" in node["data"]:
            qty = node["data"]["popularity"]

        all_categories.append(
            {
                "category_id": cat_id,
                "category_name": node.get("title", ""),
                "sale_product_qty": qty,
                "parent_category_id": parent_id,
                "is_top_level": node.get("level") == 1,
                "last_sync_at": datetime.utcnow().isoformat(),
            }
        )

        for sub_node in node.get("subNodes", []) or []:
            process_node(sub_node, cat_id)

    print("Parsing tree...")
    for root_node in raw_data.get("subNodes", []) or []:
        process_node(root_node)

    print(f"Parsed {len(all_categories)} categories. Syncing to database...")

    batch_size = 100
    success_count = 0
    for index in range(0, len(all_categories), batch_size):
        batch = all_categories[index:index + batch_size]
        try:
            supabase.table("categories").upsert(batch, on_conflict="category_id").execute()
            success_count += len(batch)
            print(f"Synced {success_count}/{len(all_categories)}")
        except Exception as error:
            print(f"Batch sync failed at index {index}: {error}")

    print(f"Full tree sync complete. Successful rows: {success_count}")


if __name__ == "__main__":
    sync_tree_to_db()
