import unittest
from datetime import datetime, timedelta

from core.task_recovery import (
    norm_category_id_for_dedup,
    select_tasks_for_recovery_requeue,
    task_category_dedup_key,
)


class RecoveryDedupTests(unittest.TestCase):
    def test_norm_category_id_for_dedup_strips_leading_zeros(self):
        self.assertEqual(norm_category_id_for_dedup("04456"), "4456")
        self.assertEqual(norm_category_id_for_dedup("00000"), "0")

    def test_select_tasks_for_recovery_requeue_dedupes_same_category(self):
        stale_before = datetime.now() - timedelta(minutes=20)
        matched = [
            {"id": "task-a", "category_id": "04456", "updated_at": "2026-01-01T00:00:00"},
            {"id": "task-b", "category_id": "4456", "updated_at": "2026-01-01T01:00:00"},
            {"id": "task-c", "category_id": "01234", "updated_at": "2026-01-01T00:00:00"},
        ]

        selected = select_tasks_for_recovery_requeue(matched, stale_before, matched)

        self.assertEqual([task["id"] for task in selected], ["task-a", "task-c"])

    def test_select_tasks_for_recovery_requeue_skips_fresh_in_flight_category(self):
        stale_before = datetime.now() - timedelta(minutes=20)
        fresh_updated_at = datetime.now().isoformat()
        stale_updated_at = (datetime.now() - timedelta(hours=2)).isoformat()

        all_tasks = [
            {"id": "fresh", "category_id": "04456", "updated_at": fresh_updated_at},
            {"id": "stale", "category_id": "04456", "updated_at": stale_updated_at},
            {"id": "other", "category_id": "01234", "updated_at": stale_updated_at},
        ]

        selected = select_tasks_for_recovery_requeue(
            [task for task in all_tasks if task["id"] != "fresh"],
            stale_before,
            all_tasks,
        )

        self.assertEqual([task["id"] for task in selected], ["other"])
        self.assertEqual(task_category_dedup_key(all_tasks[0]), task_category_dedup_key(all_tasks[1]))


if __name__ == "__main__":
    unittest.main()
