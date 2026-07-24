import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from api.server import DOWNLOAD_ROOT, _resolve_download_path
from core.final_pipeline import PGQueryBuilder


class PGQueryBuilderDeleteTests(unittest.TestCase):
    def test_delete_method_exists(self):
        builder = PGQueryBuilder("postgresql://example", "system_users")
        self.assertTrue(hasattr(builder, "delete"))
        self.assertIs(builder.delete(), builder)

    @patch("psycopg2.connect")
    def test_delete_builds_delete_query(self, mock_connect):
        mock_cursor = mock_connect.return_value.cursor.return_value
        mock_cursor.description = [("id",)]
        mock_cursor.fetchall.return_value = [{"id": "user-1"}]

        builder = PGQueryBuilder("postgresql://example", "system_users")
        response = builder.delete().eq("id", "user-1").execute()

        executed_query = mock_cursor.execute.call_args[0][0]
        self.assertIn("DELETE FROM system_users", executed_query)
        self.assertIn("WHERE id = %s", executed_query)
        self.assertEqual(response.data, [{"id": "user-1"}])


class DownloadPathTests(unittest.TestCase):
    def test_allows_file_under_output_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("api.server.DOWNLOAD_ROOT", tmpdir):
                target = os.path.join(tmpdir, "excel", "report.xlsx")
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "w", encoding="utf-8") as handle:
                    handle.write("ok")

                resolved = _resolve_download_path(target)
                self.assertEqual(resolved, os.path.abspath(target))

    def test_blocks_path_outside_output_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("api.server.DOWNLOAD_ROOT", tmpdir):
                with self.assertRaises(HTTPException) as ctx:
                    _resolve_download_path("/etc/passwd")
                self.assertEqual(ctx.exception.status_code, 403)

    def test_blocks_traversal_outside_output_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("api.server.DOWNLOAD_ROOT", tmpdir):
                outside = os.path.abspath(os.path.join(tmpdir, "..", "secret.txt"))
                with self.assertRaises(HTTPException) as ctx:
                    _resolve_download_path(outside)
                self.assertEqual(ctx.exception.status_code, 403)


class DownloadRootTests(unittest.TestCase):
    def test_download_root_points_to_output_directory(self):
        self.assertTrue(DOWNLOAD_ROOT.endswith(os.path.join("output")))
        self.assertTrue(os.path.isabs(DOWNLOAD_ROOT))


if __name__ == "__main__":
    unittest.main()
