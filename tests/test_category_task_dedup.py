import unittest
from datetime import datetime, timedelta

from api.task_dedup import (
    INFLIGHT_TASK_STATUSES,
    evaluate_category_task_block,
    norm_category_code_for_dedup,
)


class CategoryTaskDedupTests(unittest.TestCase):
    def setUp(self):
        self.recent_limit = (datetime.now() - timedelta(days=15)).isoformat()

    def test_norm_category_code_strips_leading_zeros(self):
        self.assertEqual(norm_category_code_for_dedup("04456"), "4456")
        self.assertEqual(norm_category_code_for_dedup("4456"), "4456")
        self.assertEqual(norm_category_code_for_dedup("00000"), "0")

    def test_blocks_inflight_task_for_equivalent_category_codes(self):
        tasks = [
            {
                "id": "task-1",
                "category_id": "04456",
                "status": "crawling",
                "created_at": datetime.now().isoformat(),
                "progress": 30,
            }
        ]

        blocked = evaluate_category_task_block(tasks, "4456", self.recent_limit)

        self.assertIsNotNone(blocked)
        self.assertEqual(blocked["kind"], "inflight")
        self.assertEqual(blocked["task"]["id"], "task-1")

    def test_blocks_recent_completed_task_for_equivalent_category_codes(self):
        tasks = [
            {
                "id": "task-2",
                "category_id": "4456",
                "status": "completed",
                "created_at": datetime.now().isoformat(),
            }
        ]

        blocked = evaluate_category_task_block(tasks, "04456", self.recent_limit)

        self.assertIsNotNone(blocked)
        self.assertEqual(blocked["kind"], "completed_recent")
        self.assertEqual(blocked["task"]["id"], "task-2")

    def test_allows_new_task_when_only_stale_completed_exists(self):
        tasks = [
            {
                "id": "task-3",
                "category_id": "4456",
                "status": "completed",
                "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
            }
        ]

        blocked = evaluate_category_task_block(tasks, "4456", self.recent_limit)

        self.assertIsNone(blocked)

    def test_inflight_takes_priority_over_recent_completed(self):
        tasks = [
            {
                "id": "task-running",
                "category_id": "4456",
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            },
            {
                "id": "task-done",
                "category_id": "04456",
                "status": "completed",
                "created_at": datetime.now().isoformat(),
            },
        ]

        blocked = evaluate_category_task_block(tasks, "4456", self.recent_limit)

        self.assertEqual(blocked["kind"], "inflight")
        self.assertEqual(blocked["task"]["id"], "task-running")

    def test_inflight_statuses_are_covered(self):
        for status in INFLIGHT_TASK_STATUSES:
            with self.subTest(status=status):
                tasks = [
                    {
                        "id": f"task-{status}",
                        "category_id": "4456",
                        "status": status,
                        "created_at": datetime.now().isoformat(),
                    }
                ]
                blocked = evaluate_category_task_block(tasks, "4456", self.recent_limit)
                self.assertEqual(blocked["kind"], "inflight")


if __name__ == "__main__":
    unittest.main()
