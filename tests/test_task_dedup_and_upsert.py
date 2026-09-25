import unittest
from unittest.mock import MagicMock, patch

from api.server import (
    RUNNING_TASK_STATUSES,
    _category_code_lookup_variants,
    _get_in_flight_task_for_category,
    _get_task_valid_product_count,
    _norm_category_code_for_dedup,
)
from core.final_pipeline import PGQueryBuilder


class TaskDedupHelpersTest(unittest.TestCase):
    def test_norm_category_code_strips_leading_zeros(self):
        self.assertEqual(_norm_category_code_for_dedup("004456"), "4456")
        self.assertEqual(_norm_category_code_for_dedup("00000"), "0")

    def test_lookup_variants_include_padded_and_unpadded(self):
        variants = _category_code_lookup_variants("4456")
        self.assertIn("4456", variants)
        self.assertIn("04456", variants)

    def test_get_in_flight_task_for_category_matches_other_task(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.in_.return_value.in_.return_value.execute.return_value.data = [
            {
                "id": "task-b",
                "category_id": "04456",
                "category": "儿童交通",
                "status": "crawling",
                "progress": 30,
            }
        ]

        match = _get_in_flight_task_for_category(sb, "4456", exclude_task_id="task-a")
        self.assertIsNotNone(match)
        self.assertEqual(match["id"], "task-b")

    def test_get_in_flight_task_for_category_ignores_excluded_task(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.in_.return_value.in_.return_value.execute.return_value.data = [
            {
                "id": "task-a",
                "category_id": "04456",
                "category": "儿童交通",
                "status": "crawling",
                "progress": 30,
            }
        ]

        match = _get_in_flight_task_for_category(sb, "4456", exclude_task_id="task-a")
        self.assertIsNone(match)

    def test_running_statuses_include_scraping_not_running(self):
        self.assertIn("scraping", RUNNING_TASK_STATUSES)
        self.assertNotIn("running", RUNNING_TASK_STATUSES)

    def test_empty_completed_task_is_not_considered_valid(self):
        task = {"category_stats": {"valid_product_count": 0}, "excel_path": None}
        self.assertEqual(_get_task_valid_product_count(task), 0)


class PGQueryBuilderUpsertTest(unittest.TestCase):
    @patch("psycopg2.connect")
    def test_upsert_uses_category_code_conflict_target(self, mock_connect):
        cursor = MagicMock()
        cursor.description = [("category_code",)]
        cursor.fetchone.return_value = {"category_code": "04456"}
        connection = MagicMock()
        connection.cursor.return_value = cursor
        mock_connect.return_value = connection

        builder = PGQueryBuilder("postgresql://example", "category_last_crawl_dates")
        builder.upsert(
            {
                "category_code": "04456",
                "last_crawl_date": "2026-09-25",
                "updated_at": "2026-09-25T12:00:00",
            }
        ).execute()

        query = cursor.execute.call_args[0][0]
        self.assertIn("ON CONFLICT (category_code)", query)


if __name__ == "__main__":
    unittest.main()
