import unittest

from core.rpa_category_id import resolve_niche_category_id


class ResolveNicheCategoryIdTests(unittest.TestCase):
    def test_prefers_category_id_from_rpa_payload(self):
        niche_stats = {"category_id": "00230", "category_name": "USB Flash карты"}
        self.assertEqual(resolve_niche_category_id(niche_stats), "00230")

    def test_falls_back_to_category_ext_id(self):
        niche_stats = {"category_ext_id": "01466", "category_name": "Legacy"}
        self.assertEqual(resolve_niche_category_id(niche_stats), "01466")

    def test_rpa_payload_without_category_ext_id_is_not_cleared(self):
        niche_stats = {"category_id": "00230"}
        self.assertIsNotNone(resolve_niche_category_id(niche_stats))
        self.assertNotEqual(resolve_niche_category_id(niche_stats), "")

    def test_non_dict_returns_none(self):
        self.assertIsNone(resolve_niche_category_id(None))
        self.assertIsNone(resolve_niche_category_id([]))


if __name__ == "__main__":
    unittest.main()
