import unittest

from click.testing import CliRunner

from main import main


class RelayCliTests(unittest.TestCase):
    def test_version_reports_installed_package_version(self):
        result = CliRunner().invoke(main, ["--version"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("relay, version 0.0.22", result.output)


if __name__ == "__main__":
    unittest.main()
