import unittest

from core.rpa_db_sync import (
    format_product_upsert_conflict_target,
    resolve_niche_category_id,
)


class TestRpaUpsertConflict(unittest.TestCase):
    def test_composite_primary_key_target(self):
        self.assertEqual(
            format_product_upsert_conflict_target(["sku", "task_id"]),
            "(sku, task_id)",
        )

    def test_legacy_single_primary_key_target(self):
        self.assertEqual(format_product_upsert_conflict_target(["sku"]), "(sku)")

    def test_prefers_category_id_over_ext_id(self):
        stats = {"category_id": "00002", "category_ext_id": "99999"}
        self.assertEqual(resolve_niche_category_id(stats), "00002")

    def test_falls_back_to_category_ext_id(self):
        stats = {"category_ext_id": "01466"}
        self.assertEqual(resolve_niche_category_id(stats), "01466")


if __name__ == "__main__":
    unittest.main()
