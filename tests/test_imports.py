"""Regression tests for import boundaries."""

from __future__ import annotations

import subprocess
import sys
import unittest


class ImportTests(unittest.TestCase):
    def test_approval_manager_imports_in_clean_interpreter(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from safety.approval import ApprovalManager; "
                    "from tools import ToolRegistry, create_default_registry"
                ),
            ],
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
