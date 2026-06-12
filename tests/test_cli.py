"""CLI smoke and headless core tests."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from controllers.app_context import AppContext
from core.exceptions import PolicyAbortError
from core.import_options import ImportOptions
from core.tag_central_app import TagCentralApp
from models.tag_record import TagRecord
from services.tag_repository import TagRepository

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestCLISmoke(unittest.TestCase):
    def test_main_help(self) -> None:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "main.py"), "--cli", "--help"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("tags", result.stdout)

    def test_import_help(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "main.py"),
                "--cli",
                "import",
                "proficy",
                "--help",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--conflict-action", result.stdout)


class TestTagCentralAppCLI(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "tags.csv"
        self.ctx = AppContext.create_headless()
        self.ctx.repository = TagRepository(self.db_path)
        self.ctx.tags = {
            "PUMP01": TagRecord(
                tag_name="PUMP01",
                description="MAIN PUMP",
                vessels={"VESSEL-A"},
                proficy_row_data={"Name": "PUMP01", "Description": "MAIN PUMP"},
                proficy_name="PUMP01",
                sync_status="proficy_only",
            )
        }
        self.app = TagCentralApp(self.ctx)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_status(self) -> None:
        status = self.app.status()
        self.assertEqual(status["tags"], 1)
        self.assertIn("pending_exports", status)

    def test_tags_list_json_via_cli(self) -> None:
        from cli.main import run_cli

        buffer = io.StringIO()
        with patch("cli.main.TagCentralApp", return_value=self.app):
            with redirect_stdout(buffer):
                code = run_cli(["--format", "json", "tags", "list"])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["tag_name"], "PUMP01")

    def test_show_missing_tag(self) -> None:
        from cli.main import run_cli

        with patch("cli.main.TagCentralApp", return_value=self.app):
            code = run_cli(["tags", "show", "MISSING"])
        self.assertEqual(code, 1)

    def test_proficy_import_dry_run(self) -> None:
        proficy_path = FIXTURES / "proficy_small.csv"
        if not proficy_path.exists():
            self.skipTest("fixture missing")
        result = self.app.import_proficy(
            str(proficy_path),
            "TESTVESSEL",
            ImportOptions(yes=False),
        )
        self.assertTrue(result.get("dry_run"))

    def test_proficy_import_apply_skip_conflicts(self) -> None:
        proficy_path = FIXTURES / "proficy_small.csv"
        if not proficy_path.exists():
            self.skipTest("fixture missing")
        result = self.app.import_proficy(
            str(proficy_path),
            "TESTVESSEL",
            ImportOptions(yes=True, conflict_action="skip", descriptions="auto"),
        )
        self.assertFalse(result.get("dry_run"))
        self.assertIn("summary", result)
        self.assertGreater(result["summary"]["total_rows"], 0)

    def test_descriptions_fail_policy(self) -> None:
        rows = [{"Name": "NEWTAG", "Description": ""}]
        with self.assertRaises(PolicyAbortError):
            from core.descriptions import fill_missing_descriptions_for_field

            fill_missing_descriptions_for_field(
                self.app,
                rows=rows,
                summary={"rows_missing_description_filled": 0},
                tag_field="Name",
                description_field="Description",
                descriptions_mode="fail",
            )


if __name__ == "__main__":
    unittest.main()
