import unittest

from core.category_ids import resolve_niche_category_id


class ResolveNicheCategoryIdTests(unittest.TestCase):
    def test_prefers_category_id(self):
        stats = {"category_id": "04456", "category_ext_id": "99999"}
        self.assertEqual(resolve_niche_category_id(stats), "04456")

    def test_falls_back_to_category_ext_id(self):
        stats = {"category_ext_id": "04456"}
        self.assertEqual(resolve_niche_category_id(stats), "04456")

    def test_falls_back_to_category_code(self):
        stats = {"category_code": "00123"}
        self.assertEqual(resolve_niche_category_id(stats), "00123")

    def test_empty_stats(self):
        self.assertIsNone(resolve_niche_category_id(None))
        self.assertIsNone(resolve_niche_category_id({}))


if __name__ == "__main__":
    unittest.main()
