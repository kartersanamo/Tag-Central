"""Tests for manual Cimplicity task queue."""

import tempfile
import unittest
from pathlib import Path

from services.cimplicity_manual_tasks import CimplicityManualTasks


class TestCimplicityManualTasks(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.queue_path = Path(self.temp_dir.name) / "manual_tasks.json"
        self.queue = CimplicityManualTasks(self.queue_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_add_and_clear_done(self) -> None:
        self.queue.add_task(
            vessel="C-LEGACY",
            tag_name="TAG_1",
            field="description",
            old_value="OLD",
            new_value="NEW",
            reason="manual",
        )
        self.assertEqual(self.queue.pending_count(), 1)
        task_id = self.queue.items[0].task_id
        self.queue.set_done(task_id, True)
        self.assertEqual(self.queue.pending_count(), 0)
        cleared = self.queue.clear_done()
        self.assertEqual(cleared, 1)
        self.assertEqual(len(self.queue.items), 0)

    def test_set_all_done(self) -> None:
        for index in range(3):
            self.queue.add_task(
                vessel="C-LEGACY",
                tag_name=f"TAG_{index}",
                field="address",
                old_value="A",
                new_value="B",
                reason="manual",
            )
        self.assertEqual(self.queue.pending_count(), 3)
        self.queue.set_all_done(True)
        self.assertEqual(self.queue.pending_count(), 0)


if __name__ == "__main__":
    unittest.main()

