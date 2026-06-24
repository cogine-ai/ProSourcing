import os
import unittest


class RpaUpsertConflictTests(unittest.TestCase):
    def test_production_upsert_targets_sku_primary_key(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        init_sql_path = os.path.join(repo_root, "data_assets", "database_init", "init.sql")
        pipeline_path = os.path.join(repo_root, "core", "rpa_final_pipeline.py")

        with open(init_sql_path, encoding="utf-8") as fh:
            schema = fh.read()
        with open(pipeline_path, encoding="utf-8") as fh:
            pipeline = fh.read()

        self.assertIn("sku TEXT PRIMARY KEY", schema)
        self.assertNotIn("ON CONFLICT (sku, task_id)", pipeline)
        self.assertIn("ON CONFLICT (sku) DO UPDATE SET task_id = EXCLUDED.task_id", pipeline)


if __name__ == "__main__":
    unittest.main()
