"""Tests for the multi-file apply_patch tool."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from config.config import Config
from tools.base import ToolInvocation
from tools.core.apply_patch import ApplyPatchTool


class ApplyPatchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name).resolve()
        self.tool = ApplyPatchTool(Config(cwd=self.cwd))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    async def run_patch(self, patch: str, dry_run: bool = False):
        return await self.tool.execute(
            ToolInvocation(params={"patch": patch, "dry_run": dry_run}, cwd=self.cwd)
        )

    def write(self, name: str, content: str) -> Path:
        path = self.cwd / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    async def test_multiple_operations_in_one_patch(self):
        target = self.write("a.py", "value = 1\n")
        self.write("old.py", "moved\n")

        result = await self.run_patch(
            "*** Begin Patch\n"
            "*** Update File: a.py\n"
            "<<<<<<< SEARCH\n"
            "value = 1\n"
            "=======\n"
            "value = 2\n"
            ">>>>>>> REPLACE\n"
            "*** Create File: b.py\n"
            "created = True\n"
            "*** Rename File: old.py -> nested/new.py\n"
            "*** End Patch\n"
        )

        self.assertTrue(result.success, result.error)
        self.assertEqual(target.read_text(), "value = 2\n")
        self.assertEqual((self.cwd / "b.py").read_text(), "created = True\n")
        self.assertFalse((self.cwd / "old.py").exists())
        self.assertEqual((self.cwd / "nested/new.py").read_text(), "moved\n")
        self.assertEqual(result.metadata["operations"], 3)

    async def test_several_hunks_for_one_file(self):
        target = self.write("a.py", "first = 1\nsecond = 2\n")

        result = await self.run_patch(
            "*** Begin Patch\n"
            "*** Update File: a.py\n"
            "<<<<<<< SEARCH\n"
            "first = 1\n"
            "=======\n"
            "first = 10\n"
            ">>>>>>> REPLACE\n"
            "<<<<<<< SEARCH\n"
            "second = 2\n"
            "=======\n"
            "second = 20\n"
            ">>>>>>> REPLACE\n"
            "*** End Patch\n"
        )

        self.assertTrue(result.success, result.error)
        self.assertEqual(target.read_text(), "first = 10\nsecond = 20\n")

    async def test_failing_operation_writes_nothing(self):
        target = self.write("a.py", "value = 1\n")

        result = await self.run_patch(
            "*** Begin Patch\n"
            "*** Update File: a.py\n"
            "<<<<<<< SEARCH\n"
            "value = 1\n"
            "=======\n"
            "value = 2\n"
            ">>>>>>> REPLACE\n"
            "*** Update File: missing.py\n"
            "<<<<<<< SEARCH\n"
            "nope\n"
            "=======\n"
            "still nope\n"
            ">>>>>>> REPLACE\n"
            "*** End Patch\n"
        )

        self.assertFalse(result.success)
        self.assertIn("does not exist", result.error or "")
        self.assertEqual(target.read_text(), "value = 1\n")

    async def test_ambiguous_search_is_rejected(self):
        target = self.write("a.py", "x = 1\nx = 1\n")

        result = await self.run_patch(
            "*** Begin Patch\n"
            "*** Update File: a.py\n"
            "<<<<<<< SEARCH\n"
            "x = 1\n"
            "=======\n"
            "x = 2\n"
            ">>>>>>> REPLACE\n"
            "*** End Patch\n"
        )

        self.assertFalse(result.success)
        self.assertIn("2 times", result.error or "")
        self.assertEqual(target.read_text(), "x = 1\nx = 1\n")

    async def test_dry_run_leaves_files_untouched(self):
        target = self.write("a.py", "value = 1\n")

        result = await self.run_patch(
            "*** Begin Patch\n"
            "*** Update File: a.py\n"
            "<<<<<<< SEARCH\n"
            "value = 1\n"
            "=======\n"
            "value = 2\n"
            ">>>>>>> REPLACE\n"
            "*** End Patch\n",
            dry_run=True,
        )

        self.assertTrue(result.success, result.error)
        self.assertTrue(result.metadata["dry_run"])
        self.assertEqual(target.read_text(), "value = 1\n")

    async def test_delete_and_create_of_same_path(self):
        self.write("a.py", "old\n")

        result = await self.run_patch(
            "*** Begin Patch\n"
            "*** Delete File: a.py\n"
            "*** Create File: a.py\n"
            "new\n"
            "*** End Patch\n"
        )

        self.assertTrue(result.success, result.error)
        self.assertEqual((self.cwd / "a.py").read_text(), "new\n")

    async def test_paths_outside_the_working_directory_are_rejected(self):
        result = await self.run_patch(
            "*** Begin Patch\n"
            "*** Delete File: ../escape.py\n"
            "*** End Patch\n"
        )

        self.assertFalse(result.success)
        self.assertIn("outside the working directory", result.error or "")

    async def test_confirmation_lists_operations(self):
        self.write("a.py", "value = 1\n")

        confirmation = await self.tool.get_confirmation(
            ToolInvocation(
                params={
                    "patch": (
                        "*** Begin Patch\n"
                        "*** Update File: a.py\n"
                        "<<<<<<< SEARCH\n"
                        "value = 1\n"
                        "=======\n"
                        "value = 2\n"
                        ">>>>>>> REPLACE\n"
                        "*** Delete File: a.py\n"
                        "*** End Patch\n"
                    )
                },
                cwd=self.cwd,
            )
        )

        self.assertIsNotNone(confirmation)
        assert confirmation is not None
        self.assertTrue(confirmation.is_dangerous)
        self.assertIn("Update:", confirmation.description)
        self.assertIn("Delete:", confirmation.description)


if __name__ == "__main__":
    unittest.main()
